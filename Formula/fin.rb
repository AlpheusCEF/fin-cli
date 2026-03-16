class Fin < Formula
  desc "Daily task CLI built on AlpheusCEF"
  homepage "https://github.com/AlpheusCEF/fin-cli"
  url "https://github.com/AlpheusCEF/fin-cli/releases/download/v0.1.0/fin_cli-0.1.0.tar.gz"
  sha256 "246cc3464088f0e090eb172ba9597fbf73ab00416749ce9ba5d0903b0759d08a"
  license "AGPL-3.0-or-later"

  depends_on "AlpheusCEF/tap/alph"
  depends_on "python@3.12"

  def install
    # Re-use the venv that alph created — fin is a thin layer on top.
    # If alph is installed, its libexec venv has all the shared deps.
    alph_venv = Formula["alph"].opt_libexec

    # Install fin into alph's venv so imports resolve
    system alph_venv/"bin/pip", "install", "--no-cache-dir", "--no-deps", buildpath

    bin.install_symlink alph_venv/"bin/fin"
    bin.install_symlink alph_venv/"bin/fins"
    bin.install_symlink alph_venv/"bin/fine"
  end

  test do
    assert_match "Daily task CLI", shell_output("#{bin}/fin --help")
  end
end
