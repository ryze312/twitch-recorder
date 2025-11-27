{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
  let
    systems = [
      "x86_64-linux"
      "x86_64-darwin"
      "aarch64-linux"
      "aarch64-darwin"
    ];

    getPkgsFor = system: import nixpkgs {
      inherit system;
    };

    forEachSystem = (func:
      nixpkgs.lib.genAttrs systems (system:
        func (getPkgsFor system)
      )
    );
  in

  {
    devShells = forEachSystem (pkgs: {
      default = pkgs.callPackage ./shell.nix {};
    });
  };
}
