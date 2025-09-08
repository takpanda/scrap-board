#!/usr/bin/env python3
"""
Font setup script for Japanese text rendering in Playwright screenshots.
Ensures proper font configuration for CI/testing environments.
"""

import os
import subprocess
import sys
from pathlib import Path


def check_system_fonts():
    """Check if Japanese fonts are available on the system."""
    try:
        result = subprocess.run(
            ["fc-list", ":lang=ja"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        
        if result.returncode == 0 and result.stdout.strip():
            fonts = result.stdout.strip().split('\n')
            print(f"✅ Found {len(fonts)} Japanese fonts:")
            for font in fonts[:5]:  # Show first 5 fonts
                font_name = font.split(':')[0].split('/')[-1]
                print(f"   - {font_name}")
            if len(fonts) > 5:
                print(f"   ... and {len(fonts) - 5} more")
            return True
        else:
            print("❌ No Japanese fonts found")
            return False
            
    except FileNotFoundError:
        print("❌ fontconfig (fc-list) not available")
        return False


def install_fonts():
    """Install Japanese fonts if needed."""
    print("📦 Installing Japanese fonts...")
    
    try:
        # Update package list
        subprocess.run(["sudo", "apt-get", "update"], check=True, capture_output=True)
        
        # Install Japanese fonts
        subprocess.run([
            "sudo", "apt-get", "install", "-y",
            "fonts-noto-cjk",
            "fonts-noto-cjk-extra", 
            "fonts-takao",
            "fonts-liberation"
        ], check=True, capture_output=True)
        
        # Refresh font cache
        subprocess.run(["fc-cache", "-f"], check=False, capture_output=True)
        
        print("✅ Japanese fonts installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install fonts: {e}")
        return False
    except FileNotFoundError:
        print("❌ apt-get not available (not a Debian/Ubuntu system)")
        return False


def create_font_config():
    """Create a custom font configuration for better Japanese rendering."""
    font_config = """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
    <!-- Configure Japanese font preferences -->
    <alias>
        <family>sans-serif</family>
        <prefer>
            <family>Noto Sans CJK JP</family>
            <family>TakaoPGothic</family>
            <family>Liberation Sans</family>
        </prefer>
    </alias>
    
    <alias>
        <family>serif</family>
        <prefer>
            <family>Noto Serif CJK JP</family>
            <family>TakaoPMincho</family>
            <family>Liberation Serif</family>
        </prefer>
    </alias>
    
    <alias>
        <family>monospace</family>
        <prefer>
            <family>Noto Sans Mono CJK JP</family>
            <family>TakaoGothic</family>
            <family>Liberation Mono</family>
        </prefer>
    </alias>
    
    <!-- Improve font rendering for screenshots -->
    <match target="font">
        <edit name="antialias" mode="assign">
            <bool>true</bool>
        </edit>
        <edit name="hinting" mode="assign">
            <bool>false</bool>
        </edit>
        <edit name="hintstyle" mode="assign">
            <const>hintnone</const>
        </edit>
        <edit name="rgba" mode="assign">
            <const>none</const>
        </edit>
    </match>
</fontconfig>
"""
    
    config_dir = Path.home() / ".config" / "fontconfig"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = config_dir / "fonts.conf"
    config_file.write_text(font_config)
    
    print(f"✅ Font configuration created at {config_file}")
    return True


def verify_setup():
    """Verify that the font setup is working properly."""
    print("\n🔍 Verifying font setup...")
    
    # Check system fonts
    fonts_ok = check_system_fonts()
    
    # Check font config
    config_file = Path.home() / ".config" / "fontconfig" / "fonts.conf"
    config_ok = config_file.exists()
    
    if config_ok:
        print(f"✅ Font configuration found at {config_file}")
    else:
        print("❌ Font configuration missing")
    
    # Overall status
    if fonts_ok and config_ok:
        print("\n🎉 Font setup is complete and ready for Japanese text rendering!")
        return True
    else:
        print("\n❌ Font setup incomplete")
        return False


def main():
    """Main setup function."""
    print("🔧 Setting up Japanese fonts for Playwright screenshots...\n")
    
    # Check if fonts are already available
    if not check_system_fonts():
        if not install_fonts():
            print("❌ Failed to install fonts")
            sys.exit(1)
    
    # Create font configuration
    create_font_config()
    
    # Verify setup
    if verify_setup():
        print("\n📋 Next steps:")
        print("1. Run Playwright tests with: pytest tests/test_browser.py -v")
        print("2. Check screenshot quality for Japanese text")
        print("3. If issues persist, restart your browser/system")
        sys.exit(0)
    else:
        print("\n❌ Setup failed")
        sys.exit(1)


if __name__ == "__main__":
    main()