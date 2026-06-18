[Setup]
AppId=InnoSetup 6.4.0 Brute-Force
AppName=My Password Protected Program
AppVersion=6.4.0

CreateAppDir=no
Uninstallable=no

OutputDir=.

// Random Password: 4321
Password=hA~N]pCXf7RPW*VD9v$a#;

Encryption=yes
// To check the program speed test remove comment of below line
;EncryptionKeyDerivation=pbkdf2/1000

[files]
Source: "{#CompilerPath}\Default.isl"; DestDir: "{tmp}"; Flags: IgnoreVersion DontCopy
