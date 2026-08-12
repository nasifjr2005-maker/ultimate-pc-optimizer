# Security

## Credentials

Never commit the KeyAuth application secret, GitHub tokens, or other private credentials. The public client uses KeyAuth v1.3 license endpoints, which do not require the application secret for initialization/license validation. If an application secret has been exposed, rotate it in the KeyAuth dashboard before using it elsewhere.

## System changes

PNL50 PC OPTIMIZER PRO intentionally limits optimization to reversible, user-triggered actions:

- safe temporary-file cleanup with locked files skipped
- DNS cache flush
- optional Recycle Bin emptying
- Windows High Performance power plan
- allow-listed user-app closing
- BlueStacks/MSI App Player detection
- HD-Player.exe process priority and CPU affinity
- local ADB connection target `127.0.0.1:5555`

It does not disable Windows Defender/security services, edit boot configuration, delete personal files, or modify emulator VM images.
