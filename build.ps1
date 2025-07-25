#!/usr/bin/env pwsh

# Build script for IME Helper
# This script builds the application using nuitka and prepares the release

Write-Host "Starting build process..." -ForegroundColor Green

# Step 1: Build with nuitka
Write-Host "Building application with nuitka..." -ForegroundColor Yellow
try {
    python -m nuitka --standalone --windows-console-mode=disable --windows-icon-from-ico=.\icon.ico .\ime_switcher\main.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Nuitka build completed successfully" -ForegroundColor Green
    } else {
        Write-Host "✗ Nuitka build failed" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ Error running nuitka: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Rename main.exe to ime_switcher.exe
Write-Host "Renaming executable..." -ForegroundColor Yellow
if (Test-Path "main.dist\main.exe") {
    try {
        Rename-Item -Path "main.dist\main.exe" -NewName "ime_switcher.exe"
        Write-Host "✓ Renamed main.exe to ime_switcher.exe" -ForegroundColor Green
    } catch {
        Write-Host "✗ Error renaming executable: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✗ main.dist\main.exe not found" -ForegroundColor Red
    exit 1
}

# Step 3: Copy icon.ico to main.dist/
Write-Host "Copying icon file..." -ForegroundColor Yellow
if (Test-Path ".\icon.ico") {
    try {
        Copy-Item -Path ".\icon.ico" -Destination "main.dist\" -Force
        Write-Host "✓ Copied icon.ico to main.dist/" -ForegroundColor Green
    } catch {
        Write-Host "✗ Error copying icon: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✗ icon.ico not found in current directory" -ForegroundColor Red
    exit 1
}

# Step 4: Copy config.json to main.dist/
Write-Host "Copying config file..." -ForegroundColor Yellow
if (Test-Path "ime_switcher\config.json") {
    try {
        Copy-Item -Path "ime_switcher\config.json" -Destination "main.dist\" -Force
        Write-Host "✓ Copied config.json to main.dist/" -ForegroundColor Green
    } catch {
        Write-Host "✗ Error copying config.json: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✗ ime_switcher\config.json not found" -ForegroundColor Red
    exit 1
}

# Step 5: Move main.dist to release/
Write-Host "Moving to release directory..." -ForegroundColor Yellow

# Create release directory if it doesn't exist
if (-not (Test-Path "release")) {
    New-Item -ItemType Directory -Path "release" -Force | Out-Null
    Write-Host "✓ Created release directory" -ForegroundColor Green
}

# Check if main.dist exists before moving
if (Test-Path "main.dist") {
    try {
        # If there's already a main.dist in release/, remove it first
        if (Test-Path "release\main.dist") {
            Remove-Item -Path "release\main.dist" -Recurse -Force
            Write-Host "✓ Removed existing main.dist from release directory" -ForegroundColor Green
        }
        
        Move-Item -Path "main.dist" -Destination "release\" -Force
        Write-Host "✓ Moved main.dist to release/" -ForegroundColor Green
    } catch {
        Write-Host "✗ Error moving to release directory: $_" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✗ main.dist directory not found" -ForegroundColor Red
    exit 1
}

Write-Host "🎉 Build process completed successfully!" -ForegroundColor Green
Write-Host "Built application is available in: release\main.dist\ime_switcher.exe" -ForegroundColor Cyan
