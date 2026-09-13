#!/bin/sh

### Constants
c_valgrind_min=1
keyfile=${scriptdir}/fake-passphrased.keys
passphrase="hunter2"

scenario_cmd() {
	# Try to create a cache directory with a wrong passphrase.
	setup_check "check --initialize-cachedir, bad passphrase"
	echo "wrong passphrase" |				\
		${c_valgrind_cmd} ./tarsnap --no-default-config \
		--keyfile "${keyfile}"				\
		--cachedir "${s_basename}-cachedir-${c_count_str}"	\
		--initialize-cachedir				\
		--passphrase dev:stdin-once			\
		2> "${s_basename}-${c_count_str}.stderr"
	expected_exitcode 1 $? > "${c_exitfile}"

	# Create a cache directory with the correct passphrase.
	setup_check "check --initialize-cachedir, passphrase stdin"
	echo "${passphrase}" |					\
		${c_valgrind_cmd} ./tarsnap --no-default-config \
		--keyfile "${keyfile}"				\
		--cachedir "${s_basename}-cachedir-${c_count_str}"	\
		--initialize-cachedir				\
		--passphrase dev:stdin-once			\
		2> "${s_basename}-${c_count_str}.stderr"
	echo $? > "${c_exitfile}"

	# Create a cache directory with the correct passphrase in env.
	setup_check "check --initialize-cachedir, passphrase env"
	PASSENV="hunter2"					\
		${c_valgrind_cmd} ./tarsnap --no-default-config	\
		--keyfile "${keyfile}"				\
		--cachedir "${s_basename}-cachedir-${c_count_str}"	\
		--initialize-cachedir				\
		--passphrase env:PASSENV			\
		2> "${s_basename}-${c_count_str}.stderr"
	echo $? > "${c_exitfile}"

	# Create a cache directory with the correct passphrase in a file.
	setup_check "check --initialize-cachedir, passphrase file"
	printf "hunter2\n" > "${s_basename}-passphrase.txt"
	${c_valgrind_cmd} ./tarsnap --no-default-config		\
		--keyfile "${keyfile}"				\
		--cachedir "${s_basename}-cachedir-${c_count_str}"	\
		--initialize-cachedir				\
		--passphrase "file:${s_basename}-passphrase.txt" \
		2> "${s_basename}-${c_count_str}.stderr"
	echo $? > "${c_exitfile}"

	# A passphrase file does not need a trailing newline.
	setup_check "check --initialize-cachedir, passphrase file no newline"
	printf "%s" "${passphrase}" > "${s_basename}-passphrase-nonewline.txt"
	${c_valgrind_cmd} ./tarsnap --no-default-config		\
		--keyfile "${keyfile}"				\
		--cachedir "${s_basename}-cachedir-${c_count_str}"	\
		--initialize-cachedir				\
		--passphrase "file:${s_basename}-passphrase-nonewline.txt" \
		2> "${s_basename}-${c_count_str}.stderr"
	echo $? > "${c_exitfile}"

	# A Windows-style trailing CRLF is a valid line ending.
	setup_check "check --initialize-cachedir, passphrase file CRLF"
	printf "%s\r\n" "${passphrase}" > "${s_basename}-passphrase-crlf.txt"
	${c_valgrind_cmd} ./tarsnap --no-default-config		\
		--keyfile "${keyfile}"				\
		--cachedir "${s_basename}-cachedir-${c_count_str}"	\
		--initialize-cachedir				\
		--passphrase "file:${s_basename}-passphrase-crlf.txt" \
		2> "${s_basename}-${c_count_str}.stderr"
	echo $? > "${c_exitfile}"

	# An embedded CR must be rejected instead of truncating the passphrase.
	setup_check "check --initialize-cachedir, reject passphrase file stray CR"
	cr_passfile="${s_basename}-passphrase-cr.txt"
	cr_cachedir="${s_basename}-cachedir-${c_count_str}"
	cr_stderr="${s_basename}-${c_count_str}.stderr"
	printf "%s\rextra\n" "${passphrase}" > "${cr_passfile}"
	${c_valgrind_cmd} ./tarsnap --no-default-config		\
		--keyfile "${keyfile}"				\
		--cachedir "${cr_cachedir}"			\
		--initialize-cachedir				\
		--passphrase "file:${cr_passfile}" \
		2> "${cr_stderr}"
	cr_status=$?
	if [ "${cr_status}" -eq "${valgrind_exit_code}" ]; then
		echo "${valgrind_exit_code}" > "${c_exitfile}"
	elif [ "${cr_status}" -eq 1 ] &&			\
	    grep -q "carriage return or newline" "${cr_stderr}" &&	\
	    [ ! -e "${cr_cachedir}" ]; then
		echo "0" > "${c_exitfile}"
	else
		echo "1" > "${c_exitfile}"
	fi
}
