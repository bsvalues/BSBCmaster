{pkgs}: {
  deps = [
    pkgs.libxcrypt
    pkgs.unixODBC
    pkgs.postgresql
    pkgs.openssl
  ];
}
