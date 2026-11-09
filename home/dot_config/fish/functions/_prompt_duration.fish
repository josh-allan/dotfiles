# 850ms, 4.2s, 3m12s
function _prompt_duration --argument-names ms
    if test $ms -lt 1000
        echo {$ms}ms
    else if test $ms -lt 60000
        echo (math -s1 $ms / 1000)s
    else
        echo (math "floor($ms / 60000)")m(math "floor($ms % 60000 / 1000)")s
    end
end
