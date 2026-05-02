function push
    set -gx upstream (git branch | sed -n '/\* /s///p')
    git push origin {$upstream} $argv
end
