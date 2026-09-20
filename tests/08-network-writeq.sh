#!/bin/sh

scenario_cmd() {
	setup_check "network writeq cancellation makes progress"

	root=$(CDPATH='' cd -- "${scriptdir}/.." && pwd -P)
	testbin="${out}/network-writeq"

	${CC:-cc} -std=c99 -O2 -Wall -Wextra -Werror \
	    -I"${root}/lib/network" -I"${root}/lib-platform/network" \
	    -I"${root}/lib/util" "${root}/tests/unit/network-writeq.c" \
	    "${root}/lib/network/tsnetwork_writeq.c" -o "${testbin}"
	rc=$?
	if [ "${rc}" -eq 0 ]; then
		"${testbin}"
		rc=$?
	fi
	echo "${rc}" > "${c_exitfile}"
}
