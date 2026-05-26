# Loader: source all per-function files under ./functions/
# Each file under functions/ defines a single shell function (named after the file).
for _f in "${0:A:h}/functions/"*.sh(N); do
  source "$_f"
done
unset _f
