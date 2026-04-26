function extract -d 'unarchive any file type'
  if test (count $argv) -ne 1
    echo "Error: No file specified."
    return 1
  end
  set -l f $argv
  if test -f $f
    switch $f
      case '*.tar.bz2' '*.tbz2'
        tar xvjf $f
      case '*.tar.gz' '*.tgz'
        tar xvzf $f
      case '*.tar.xz' '*.txz'
        tar xvJf $f
      case '*.tar.zst' '*.tzst'
        zstd -dc $f | tar xv -
      case '*.tar.lz4'
        lz4 -dc $f | tar xv -
      case '*.tar.lzo' '*.tzo'
        lzop -dc $f | tar xv -
      case '*.tar.lzma'
        xz -dc --format=lzma $f | tar xv -
      case '*.tar'
        tar xvf $f
      case '*.bz2'
        bunzip2 $f
      case '*.gz'
        gunzip $f
      case '*.xz'
        xz -d $f
      case '*.zst'
        zstd -d $f
      case '*.lz4'
        lz4 -d $f
      case '*.lzo'
        lzop -d $f
      case '*.lzma'
        xz -d --format=lzma $f
      case '*.rar'
        unrar x $f
      case '*.zip' '*.war' '*.jar' '*.ear'
        unzip $f
      case '*.Z'
        uncompress $f
      case '*.7z' '*.cab'
        7z x $f
      case '*.deb'
        ar x $f
      case '*.rpm'
        rpm2cpio $f | cpio -idmv
      case '*.pkg'
        xar -xf $f
      case '*'
        echo "'$f' cannot be extracted"
    end
  else
    echo "'$f' is not a valid file"
  end
end
