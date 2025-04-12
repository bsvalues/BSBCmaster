{pkgs}: {
  deps = [
    pkgs.rustc
    pkgs.libiconv
    pkgs.cargo
    pkgs.libyaml
    pkgs.glibcLocales
    pkgs.jq
    pkgs.libxcrypt
    pkgs.unixODBC
    pkgs.postgresql
    pkgs.openssl
  ];
}
