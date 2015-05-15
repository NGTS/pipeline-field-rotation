#!/usr/bin/env sh

set -e

main() {
    cat all_dirs.txt | while read dirname; do
        OUTNAME="${PWD}/$(echo $dirname | cut -d / -f 6).png"
        echo ./venv/bin/python ./run_on_files.py $dirname -o /dev/null -p ${OUTNAME} | qsub -cwd -pe parallel 12 -S /bin/bash 
    done
}

main
