// swift-tools-version: 5.9
//
// Package.swift
// popo/examples/swift
//
// Copyright © 2026 Dagitali LLC. All rights reserved.
//
// Minimal Swift package for demonstrating repository guardrail adoption.

import PackageDescription

let package = Package(
    name: "GuardrailExample",
    products: [.library(name: "GuardrailExample", targets: ["GuardrailExample"])],
    targets: [
        .target(name: "GuardrailExample"),
        .testTarget(name: "GuardrailExampleTests", dependencies: ["GuardrailExample"]),
    ]
)
