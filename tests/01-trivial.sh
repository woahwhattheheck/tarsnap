#!/bin/sh

### Constants
c_valgrind_min=1
version_stdout=${s_basename}-version.stdout
help_stdout=${s_basename}-help.stdout
no_args_stderr=${s_basename}-no-args.stderr
keylist_stderr=${s_basename}-keylist.stderr

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
}
