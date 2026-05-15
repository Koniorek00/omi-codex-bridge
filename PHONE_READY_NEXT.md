# Phone Ready Next

Phone is authorized now. Keep normal operation in quiet mode:

1. Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
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
Powiedz Codexowi zeby pokazal na telefonie: test z Omi
```

6. Verify:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\doctor.ps1
```

Keep autorun off unless the user explicitly changes that safety decision.

Auto-start is already installed through the Startup shortcut fallback:

```text
C:\Users\wikto\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Omi Codex Bridge Watchdog.lnk
```

The hidden watcher runs:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\watch_stack.ps1 -Port 8766 -EveryMinutes 15
```

Visible phone control is opt-in only:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\wait_for_android.ps1 -OpenOmi -StartScrcpy
```
