function install_proton_ge --description "Install latest Proton GE custom build for this machine's architecture"
    # Releases ship one tarball per architecture (x86_64, aarch64); pick ours.
    set arch (uname -m)

    echo "Fetching latest release assets for $arch..."
    set urls (curl -fsSL https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest | string match -rag '"browser_download_url":\s*"([^"]+)"')
    set tarball_url (string match -r -- "^.*-$arch\.tar\.gz\$" $urls)
    set checksum_url (string match -r -- "^.*-$arch\.sha512sum\$" $urls)

    if test (count $tarball_url) -ne 1 -o (count $checksum_url) -ne 1
        echo "Error: expected one $arch tarball and checksum in the latest release, found:" >&2
        printf '  %s\n' $urls >&2
        return 1
    end

    set workdir (mktemp -d -t proton-ge-custom.XXXXXX)
    or return 1
    set tarball $workdir/(basename $tarball_url)
    set checksum $workdir/(basename $checksum_url)

    echo "Downloading "(basename $tarball)"..."
    curl -fL --progress-bar $tarball_url -o $tarball
    and curl -fsSL $checksum_url -o $checksum
    or begin
        echo "Error: download failed" >&2
        rm -rf $workdir
        return 1
    end

    echo "Verifying checksum..."
    # The .sha512sum file names the tarball by basename, so check from its directory.
    if not fish -c 'cd $argv[1]; and sha512sum -c $argv[2]' $workdir (basename $checksum)
        echo "Error: checksum verification failed" >&2
        rm -rf $workdir
        return 1
    end

    mkdir -p ~/.steam/root/compatibilitytools.d
    echo "Extracting to ~/.steam/root/compatibilitytools.d..."
    tar -xf $tarball -C ~/.steam/root/compatibilitytools.d/
    set tar_status $status
    rm -rf $workdir
    test $tar_status -eq 0; or return $tar_status
    echo "Installed "(basename $tarball .tar.gz)"."

    # Steam only scans compatibilitytools.d at startup.
    if pgrep -x steam >/dev/null
        echo "Shutting down Steam so it picks up the new build on next launch..."
        steam -shutdown >/dev/null 2>&1
        for i in (seq 30)
            pgrep -x steam >/dev/null; or break
            sleep 1
        end
        if pgrep -x steam >/dev/null
            echo "Steam still running after 30s; killing it."
            pkill -x steam
        end
    end
end
