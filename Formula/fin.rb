class Fin < Formula
  desc "Daily task CLI built on AlpheusCEF"
  homepage "https://github.com/AlpheusCEF/fin-cli"
  url "https://github.com/AlpheusCEF/fin-cli/releases/download/v0.1.0/fin_cli-0.1.0.tar.gz"
  sha256 "246cc3464088f0e090eb172ba9597fbf73ab00416749ce9ba5d0903b0759d08a"
  license "AGPL-3.0-or-later"

  preserve_rpath

  depends_on "python@3.12"

  resource "alph-cli" do
    url "https://github.com/AlpheusCEF/alph-cli/releases/download/v0.1.35/alph_cli-0.1.35.tar.gz"
    sha256 "4de3b76b3d3807c03e42a9d235a6568f39de10f3fe580a439eb029ec5aa03bb0"
  end

  def install
    python3 = Formula["python@3.12"].opt_bin/"python3.12"
    system python3, "-m", "venv", libexec

    # Install alph-cli first (fin's dependency)
    resource("alph-cli").stage do
      system libexec/"bin/pip", "install", "--no-cache-dir", "."
    end

    # Install fin-cli
    system libexec/"bin/pip", "install", "--no-cache-dir", "--no-deps", buildpath

    bin.install_symlink libexec/"bin/fin"
    bin.install_symlink libexec/"bin/fins"
    bin.install_symlink libexec/"bin/fine"
  end

  test do
    assert_match "Daily task CLI", shell_output("#{bin}/fin --help")
  end
end
