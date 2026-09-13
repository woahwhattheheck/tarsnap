#!/bin/sh

### Constants
c_valgrind_min=1

scenario_cmd() {
	# Reject NaN before later command-line validation can mask the parse error.
	setup_check "keymgmt rejects NaN --passphrase-time"
	${c_valgrind_cmd} ./tarsnap-keymgmt --passphrase-time NaN \
		2> "${s_basename}-${c_count_str}.stderr"
	grep -Fq "Invalid --passphrase-time argument: NaN" \
		"${s_basename}-${c_count_str}.stderr"
	echo $? > "${c_exitfile}"

	# Reject a valid numeric prefix followed by non-numeric text.
	setup_check "keymgmt rejects trailing --passphrase-time text"
	${c_valgrind_cmd} ./tarsnap-keymgmt --passphrase-time 1junk \
		2> "${s_basename}-${c_count_str}.stderr"
	grep -Fq "Invalid --passphrase-time argument: 1junk" \
		"${s_basename}-${c_count_str}.stderr"
	echo $? > "${c_exitfile}"
}
