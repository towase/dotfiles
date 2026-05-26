# pnpick: pick a pnpm workspace package + script via fzf and run it.
# Requires: pnpm, jq, fzf
pnpick() {
  if ! command -v pnpm >/dev/null || ! command -v jq >/dev/null || ! command -v fzf >/dev/null; then
    print -u2 "pnpick: requires pnpm, jq and fzf in PATH"
    return 1
  fi

  local list
  list=$(pnpm -r list --depth -1 --json 2>/dev/null) || {
    print -u2 "pnpick: run inside a pnpm workspace"
    return 1
  }

  local pkg_line
  pkg_line=$(print -r -- "$list" \
    | jq -r '.[] | select(.name != null) | "\(.name)\t\(.path)"' \
    | fzf --delimiter=$'\t' --with-nth=1 \
          --prompt='package> ' \
          --preview 'jq -r ".scripts // {} | keys[]?" {2}/package.json' \
          --preview-window=right:50%:wrap) || return 130
  [[ -z "$pkg_line" ]] && return 130

  local pkg_name="${pkg_line%%$'\t'*}"
  local pkg_path="${pkg_line##*$'\t'}"

  local script_line
  script_line=$(jq -r '.scripts // {} | to_entries[] | "\(.key)\t\(.value | gsub("\n";" ") | gsub("\t";" "))"' "$pkg_path/package.json" \
    | fzf --delimiter=$'\t' --with-nth=1 \
          --prompt="${pkg_name} > script> " \
          --preview 'echo {2}' \
          --preview-window=down:3:wrap) || return 130
  [[ -z "$script_line" ]] && return 130

  local script_name="${script_line%%$'\t'*}"

  print -P "%F{cyan}» pnpm --filter ${pkg_name} ${script_name}%f"
  pnpm --filter "$pkg_name" "$script_name"
}
