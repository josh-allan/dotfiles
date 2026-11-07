function klogin --argument-names cluster
    if test (count $argv) -ne 1
        echo "Usage: klogin prod|staging"
        return 1
    end

    if test "$cluster" != prod; and test "$cluster" != staging
        echo "Invalid cluster. Use 'prod' or 'staging'."
        return 1
    end

    set -gx KUBECONFIG ~/.kube/config.$cluster
    set -gx CLOUDOPS_API "https://api.$cluster.corp.mongodb.com/cloud-ops"
    set -l namespace cloud-ops

    mkdir -p (dirname $KUBECONFIG)

    if not test -f $KUBECONFIG
        echo "klogin: initial kubeconfig setup for $cluster"
        kanopy-oidc kube setup $cluster >$KUBECONFIG
    end

    kanopy-oidc kube login
    kubectl config set-context (kubectl config current-context) --namespace=$namespace

    echo "klogin: now using $cluster (KUBECONFIG=$KUBECONFIG, CLOUDOPS_API=$CLOUDOPS_API)"
end

function kget
    if test (count $argv) -ne 2
        echo 'USAGE: kget "<deployments | pods | ...>" "<regex>"'
        return 1
    end

    set -l resource "$argv[1]"
    set -l glob "$argv[2]"

    kubectl get $resource -o json \
        | jq -r ".items | map(select(.metadata.name | test(\"$glob\"))) | {kind: \"List\", items: .}" \
        | kubectl get -f -
end

function klog --description "fzf-select a pod and tail its logs"
    if test (count $argv) -gt 1
        echo 'USAGE: klog "[optional name query]"'
        return 1
    end

    set -l query ""
    if test (count $argv) -eq 1
        set query $argv[1]
    end

    kubectl get pods --no-headers \
        | fzf --query "$query" \
        --preview 'kubectl logs --tail=200 {1}' \
        --preview-window=right:50% \
        --bind "enter:become(echo 'klog: tailing logs for {1}'; kubectl logs -f {1})"
end

function kexec --description "Exec into a pod matched by name pattern"
    kubectl get pods --no-headers \
        | fzf --query "$argv[1]" \
        --preview 'kubectl describe pod {1}' \
        --preview-window=right:50% \
        --bind "enter:become(echo 'kexec: entering pod {1}'; kubectl exec -it {1} -- sh)"
end

function kgrep --description "fzf-select a pod and grep its logs for a pattern"
    if test (count $argv) -lt 1 -o (count $argv) -gt 2
        echo 'USAGE: kgrep "<pattern>" ["[optional pod name query]"]'
        return 1
    end

    set -l pattern $argv[1]
    set -l query ""
    if test (count $argv) -eq 2
        set query $argv[2]
    end

    kubectl get pods --no-headers \
        | fzf --query "$query" \
        --preview "kubectl logs --tail=200 {1} | grep --color=always -i -- '$pattern' || true" \
        --preview-window=right:50% \
        --bind "enter:become(echo 'kgrep: searching logs for {1} with pattern \"$pattern\"'; kubectl logs {1} | grep -i -- '$pattern')"
end
