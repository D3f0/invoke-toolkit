from textwrap import dedent

# TODO: Find a way to extract this automatically...
# Original code from invoke:
# Grab all .completion files in invoke/completion/. (These used to have no
# suffix, but surprise, that's super fragile.

completions = {
    "bash": dedent(
        """

    # Invoke tab-completion script to be sourced with Bash shell.
    # Known to work on Bash 3.x, untested on 4.x.

    _complete_{binary}() {{
        local candidates

        # COMP_WORDS contains the entire command string up til now (including
        # program name).
        # We hand it to Invoke so it can figure out the current context: spit back
        # core options, task names, the current task's options, or some combo.
        candidates=`{binary} --complete -- ${{COMP_WORDS[*]}}`

        # `compgen -W` takes list of valid options & a partial word & spits back
        # possible matches. Necessary for any partial word completions (vs
        # completions performed when no partial words are present).
        #
        # $2 is the current word or token being tabbed on, either empty string or a
        # partial word, and thus wants to be compgen'd to arrive at some subset of
        # our candidate list which actually matches.
        #
        # COMPREPLY is the list of valid completions handed back to `complete`.
        COMPREPLY=( $(compgen -W "${{candidates}}" -- $2) )
    }}


    # Tell shell builtin to use the above for completing our invocations.
    # * -F: use given function name to generate completions.
    # * -o default: when function generates no results, use filenames.
    # * positional args: program names to complete for.
    complete -F _complete_{binary} -o default {spaced_names}

    # vim: set ft=sh :
               """
    ),
    "zsh": dedent(
        """
    # Invoke tab-completion script to be sourced with the Z shell.
    # Known to work on zsh 5.0.x, probably works on later 4.x releases as well (as
    # it uses the older compctl completion system).

    _complete_{binary}() {{
        # `words` contains the entire command string up til now (including
        # program name).
        #
        # We hand it to Invoke so it can figure out the current context: spit back
        # core options, task names, the current task's options, or some combo.
        #
        # Before doing so, we attempt to tease out any collection flag+arg so we
        # can ensure it is applied correctly.
        collection_arg=''
        if [[ "${{words}}" =~ "(-c|--collection) [^ ]+" ]]; then
            collection_arg=$MATCH
        fi
        # `reply` is the array of valid completions handed back to `compctl`.
        # Use ${{=...}} to force whitespace splitting in expansion of
        # $collection_arg
        reply=( $({binary} ${{=collection_arg}} --complete -- ${{words}}) )
    }}


    # Tell shell builtin to use the above for completing our given binary name(s).
    # * -K: use given function name to generate completions.
    # * +: specifies 'alternative' completion, where options after the '+' are only
    #   used if the completion from the options before the '+' result in no matches.
    # * -f: when function generates no results, use filenames.
    # * positional args: program names to complete for.
    compctl -K _complete_{binary} + -f {spaced_names}

    # vim: set ft=sh :
    """
    ),
    "fish": dedent(
        """
    # Invoke tab-completion script for the fish shell
    # Copy it to the ~/.config/fish/completions directory

    function __complete_{binary}
        {binary} --complete -- (commandline --tokenize)
    end

    # --no-files: Don't complete files unless invoke gives an empty result
    # TODO: find a way to honor all binary_names
    complete --command {binary} --no-files --arguments '(__complete_{binary})'
                   """
    ),
}
