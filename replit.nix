{pkgs}: {
  deps = [
    pkgs.libyaml
    pkgs.glibcLocales
    pkgs.jq
    pkgs.libxcrypt
    pkgs.unixODBC
    pkgs.postgresql
    pkgs.openssl
  ];
}
