on run
  set mainAppName to "CGV Presenter.app"

  try
    set installerBundle to POSIX path of (path to me)
    set installDir to do shell script "dirname " & quoted form of installerBundle
    set sourceApp to installDir & "/" & mainAppName
    set targetApp to "/Applications/" & mainAppName

    try
      do shell script "test -d " & quoted form of sourceApp
    on error
      display dialog "Could not find CGV Presenter in the same folder as this installer." & return & return & "Please unzip the full download, then double-click Install CGV Presenter again." buttons {"OK"} default button "OK" with icon stop with title "CGV Presenter Setup"
      return
    end try

    display dialog "This will install CGV Presenter in your Applications folder." & return & return & "Because CGV Presenter is distributed directly by Cultivados en Gracia y Verdad (not through the Mac App Store), macOS requires a one-time local setup step." & return & return & "Click Install to continue." buttons {"Cancel", "Install"} default button "Install" with title "CGV Presenter Setup"

    do shell script "rm -rf " & quoted form of targetApp
    do shell script "cp -R " & quoted form of sourceApp & " " & quoted form of targetApp
    do shell script "xattr -cr " & quoted form of targetApp

    set launchChoice to button returned of (display dialog "CGV Presenter was installed successfully." & return & return & "You can open it from Applications like any other app." buttons {"Done", "Open CGV Presenter"} default button "Open CGV Presenter" with title "CGV Presenter Setup")

    if launchChoice is "Open CGV Presenter" then
      do shell script "open " & quoted form of targetApp
    end if
  on error errMsg
    display dialog "Installation could not be completed." & return & return & errMsg buttons {"OK"} default button "OK" with icon stop with title "CGV Presenter Setup"
  end try
end run
