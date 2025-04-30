function kget
    if test (count $argv) -ne 2
        echo "USAGE: kget \"<deployments | pods>\" \"<glob>\""
        return 1
    end

    set -l resource "$argv[1]"
    set -l glob "$argv[2]"

    kubectl get $resource -o json | jq -r ".items | map(select(.metadata.name | test(\"$glob\"))) | {kind: \"List\", items: .}" | kubectl get -f -
end

function klog
    if test (count $argv) -ne 1
        echo "USAGE: klog \"<glob>\""
        echo ""
        echo "NOTE: this assumed that the first pod returned is the one you want to tail the logs of. If you're tailing the wrong logs, make the glob more targeted."
        return 1
    end

    set -l glob "$argv[1]"
    set -l pod $(kubectl get pods -o json | jq -r ".items | map(select(.metadata.name | test(\"$glob\")))[0].metadata.name")

    kubectl logs -f "$pod"
end

function klogin --argument-names cluster
    if test "$cluster" != prod -a "$cluster" != staging
        echo "Invalid cluster. Use 'prod' or 'staging'."
        return 1
    end

    set namespace cloud-ops
    set -l old_kubeconfig $KUBECONFIG
    set -x KUBECONFIG ~/.kube/config.$cluster
    mkdir -p (dirname $KUBECONFIG)
    kanopy-oidc kube setup $cluster >$KUBECONFIG
    kanopy-oidc kube login
    kubectl config set-context (kubectl config current-context) --namespace=$namespace
    set -x KUBECONFIG $old_kubeconfig
end
