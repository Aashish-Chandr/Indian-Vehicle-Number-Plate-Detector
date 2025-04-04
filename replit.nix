{pkgs}: {
  deps = [
    pkgs.glibcLocales
    pkgs.tesseract
    pkgs.libGLU
    pkgs.libGL
    pkgs.postgresql
    pkgs.openssl
  ];
}
