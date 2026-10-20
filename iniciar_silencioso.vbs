Set WshShell = CreateObject("WScript.Shell")
strCurDir = WshShell.CurrentDirectory
WshShell.Run "pythonw.exe """ & strCurDir & "\main.py""", 0, False
