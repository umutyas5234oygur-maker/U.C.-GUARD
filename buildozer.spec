[app]
title = UC GUARD
package.name = ucguard
package.domain = org.ucguard

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,ttf
source.exclude_dirs = .git,.github,bin,.buildozer,__pycache__

# ZORUNLU: bu satır yoksa Buildozer saniyeler içinde hata verir
version = 0.1

# main.py'nin import ettiği TÜM üçüncü parti kütüphaneleri buraya ekle
requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True
android.allow_backup = True

[buildozer]
log_level = 2
warn_on_root = 1
p4a.branch = v2024.01.21
