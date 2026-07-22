; NSIS hooks for the Owlet Dashboard installer.
;
; The app bundles a sidecar (owlet-server.exe) that runs as its own process.
; NSIS's built-in "close the running app" logic only knows about the main
; window exe, so if the sidecar is still running the installer fails to
; overwrite it with "Error opening file for writing". Kill it before we touch
; any files, on both install and uninstall. /T also takes any child processes.

!macro NSIS_HOOK_PREINSTALL
  nsExec::Exec 'taskkill /F /IM owlet-server.exe /T'
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  nsExec::Exec 'taskkill /F /IM owlet-server.exe /T'
!macroend
