# Phone Ready Next

When ADB changes from `unauthorized` to `device`:

1. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\wait_for_android.ps1 -OpenOmi -StartScrcpy
```

2. In Omi, create or edit the Codex bridge integration.

3. Use the private setup sheet:

```text
runtime\omi-setup-urls.private.txt
```

4. Copy fields one by one:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\copy_setup_url.ps1 -Name home
powershell -ExecutionPolicy Bypass -File .\scripts\copy_setup_url.ps1 -Name setup
powershell -ExecutionPolicy Bypass -File .\scripts\copy_setup_url.ps1 -Name realtime
powershell -ExecutionPolicy Bypass -File .\scripts\copy_setup_url.ps1 -Name memory
powershell -ExecutionPolicy Bypass -File .\scripts\copy_setup_url.ps1 -Name manifest
```

5. Test phrase:

```text
Hey Omi Codex queue a tiny smoke test task
```

6. Verify:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
```

Keep autorun off unless the user explicitly changes that safety decision.
