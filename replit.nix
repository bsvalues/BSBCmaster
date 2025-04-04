{pkgs}: {
  deps = [
    pkgs.jq
    pkgs.libxcrypt
    pkgs.unixODBC
    pkgs.postgresql
    pkgs.openssl
  ];
}
