// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "ClipMindMenuBar",
    platforms: [.macOS(.v13)],
    products: [.executable(name: "ClipMindMenuBar", targets: ["ClipMindMenuBar"])],
    targets: [
        .executableTarget(name: "ClipMindMenuBar"),
        .testTarget(name: "ClipMindMenuBarTests", dependencies: ["ClipMindMenuBar"])
    ]
)
