set -e

craftRoot="${BASH_SOURCE[0]}"
if [[ -z "$craftRoot" ]];then
    craftRoot="$0"
fi
if [[ -z "$craftRoot" ]];then
    craftRoot="$_"
fi
if [[ -z "$craftRoot" ]];then
    echo "Failed to determine interpreter"
    exit 1
fi

if [[ ! -d "$craftRoot" ]]; then
    craftRoot=$(python3.6 -c "import os; import sys; print(os.path.dirname(os.path.abspath(sys.argv[1])));" "$craftRoot")
fi

export craftRoot

CRAFT_ENV=($(python3.6 "$craftRoot/bin/CraftSetupHelper.py" --setup))
# Split the CraftSetupHelper.py output by newlines instead of any whitespace
# to also handled environment variables containing spaces (e.g. $PS1)
# See https://stackoverflow.com/q/24628076/894271
function export_lines() {
    local IFS=$'\n'
    local lines=($1)
    local i
    for (( i=0; i<${#lines[@]}; i++ )) ; do
        local line=${lines[$i]}
        if [[ "$line"  =~ "=" ]] && [[ $line != _=* ]] ; then
            export "$line" || true
        fi
    done
}
export_lines "$CRAFT_ENV"

cs() {
    dir=$($craftRoot/bin/craft -q --ci-mode --get "sourceDir()" $1)
    if (($? > 0));then
        echo $dir
    else
        cd "$dir"
    fi
}

cb() {
    dir=$($craftRoot/bin/craft -q --ci-mode --get "buildDir()" $1)
    if (($? > 0));then
        echo $dir
    else
        cd "$dir"
    fi
}

cr() {
    cd "$KDEROOT"
}

cr

declare -x -F cs cb cr
