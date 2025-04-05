{pkgs}: {
  deps = [
    pkgs.glibcLocales
    pkgs.jq
    pkgs.libxcrypt
    pkgs.unixODBC
    pkgs.postgresql
    pkgs.openssl
  ];
}
