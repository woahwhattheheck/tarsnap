#!/bin/sh

### Constants
c_valgrind_min=1
version_stdout=${s_basename}-version.stdout
help_stdout=${s_basename}-help.stdout
no_args_stderr=${s_basename}-no-args.stderr
keylist_stderr=${s_basename}-keylist.stderr
cpio_bad=${s_basename}-invalid-newc.cpio
cpio_stderr=${s_basename}-cpio.stderr
cpio_timeout=${s_basename}-cpio.timeout

scenario_cmd() {
	# Check --help.
	setup_check "check --help"
	${c_valgrind_cmd} ./tarsnap --no-default-config		\
	    --help > "${help_stdout}"
	echo $? > "${c_exitfile}"

	# Check --version.
	setup_check "check --version"
	${c_valgrind_cmd} ./tarsnap --no-default-config		\
	    --version > "${version_stdout}"
	echo $? > "${c_exitfile}"

	setup_check "check --version output"
	grep -q "tarsnap" "${version_stdout}"
	echo $? > "${c_exitfile}"

	# Check no arguments (expect exit code 1, error message).
	setup_check "check no arguments"
	${c_valgrind_cmd} ./tarsnap --no-default-config		\
	    2> "${no_args_stderr}"
	expected_exitcode 1 $? > "${c_exitfile}"

	setup_check "check no arguments output"
	grep -q "tarsnap: Must specify one of" "${no_args_stderr}"
	echo $? > "${c_exitfile}"

	# --keylist entries must consist entirely of a valid key number.
	setup_check "check malformed --keylist number"
	${c_valgrind_cmd} ./tarsnap-keymgmt --keylist 1junk	\
	    --outkeyfile "${s_basename}-bad.keys" 2> "${keylist_stderr}"
	expected_exitcode 1 $? > "${c_exitfile}"

	setup_check "check malformed --keylist diagnostic"
	grep -q "Not a valid key number: 1junk" "${keylist_stderr}"
	echo $? > "${c_exitfile}"

	# A malformed newc header which is exactly one fixed header long used to
	# make libarchive's resynchronization loop consume zero bytes forever.
	printf '070701' > "${cpio_bad}"
	_i=0
	while [ "${_i}" -lt 104 ]; do
		printf '0' >> "${cpio_bad}"
		_i=$((_i + 1))
	done
	printf 'G' | dd of="${cpio_bad}" bs=1 seek=12 conv=notrunc 2>/dev/null

	setup_check "check malformed newc cpio terminates"
	rm -f "${cpio_timeout}"
	./tarsnap --no-default-config -c --dry-run @"${cpio_bad}"	\
	    2> "${cpio_stderr}" &
	_cpio_pid=$!
	(
		sleep 3
		: > "${cpio_timeout}"
		kill -TERM "${_cpio_pid}" 2>/dev/null || true
	) &
	_watchdog_pid=$!
	wait "${_cpio_pid}"
	_cpio_status=$?
	kill "${_watchdog_pid}" 2>/dev/null || true
	wait "${_watchdog_pid}" 2>/dev/null || true
	if [ -f "${cpio_timeout}" ] || [ "${_cpio_status}" -eq 0 ]; then
		echo 1 > "${c_exitfile}"
	else
		echo 0 > "${c_exitfile}"
	fi
}
