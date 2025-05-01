function forcekill
  kill (ps ax | grep -i $argv[1] | awk '{ print $1 }')
end