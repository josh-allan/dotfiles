// Widevine DRM — required because Zen on Linux has no UI toggle and
// does not read system Firefox pref files (AppImage packaging).
// MOZ_GMP_PATH must point to /var/lib/widevine/gmp-widevinecdm/system-installed
// (set via /usr/lib/environment.d/50-gmpwidevine.conf by widevine-installer).
user_pref("media.eme.enabled", true);
user_pref("media.eme.encrypted-media-encryption-scheme.enabled", true);
user_pref("media.gmp-widevinecdm.enabled", true);
user_pref("media.gmp-widevinecdm.visible", true);
user_pref("media.gmp-widevinecdm.version", "system-installed");
user_pref("media.gmp-widevinecdm.autoupdate", false);
