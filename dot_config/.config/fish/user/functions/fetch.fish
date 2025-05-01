function fetch
    set -gx upstream $(git branch | sed -n '/\* /s///p')
    git fetch && git pull origin {$upstream}
end
