$comdirectURL = "https://kunde.comdirect.de/lp/wt/login?execution=e1s1&afterTimeout=true"

$env:PATH += ";$PSScriptRoot" # Adds the path for ChromeDriver.exe to the environmental variable 
Add-Type -Path "$PSScriptRoot\WebDriver.dll" # Adding Selenium's .NET assembly (dll) to access it's classes in this PowerShell session
Add-Type -Path "$PSScriptRoot\WebDriver.Support.dll" # Adding Selenium's .NET assembly (dll) to access it's classes in this PowerShell session
$ChromeDriver = New-Object OpenQA.Selenium.Chrome.ChromeDriver # Creates an instance of this class to control Selenium and stores it in an easy to handle variable



# Settings.ini should contain two lines: user=xxxx and pass=xxxx with your comdirect credentials. Obviously: NEVER share these!!!
$settings = Get-Content $PSScriptRoot\settings.ini | ConvertFrom-StringData

$postBoxDir = "$PSScriptRoot\Dokumente"
if ([System.IO.Path]::IsPathRooted($settings.outputdir)) {
    $postBoxDir = $settings.outputdir
} else {
    $postBoxDir = "$PSScriptRoot\" + $settings.outputdir
}
# Create Folder if it doesn't exist
New-Item -Force -ItemType directory -Path $postBoxDir | Out-Null




# Let's go to the website
$ChromeDriver.Navigate().GoToURL($comdirectURL)

# Let's enter our credentials
$ChromeDriver.FindElementByName("param1").SendKeys($settings.user)
$ChromeDriver.FindElementByName("param3").SendKeys($settings.pass)
$ChromeDriver.FindElementById("loginAction").Click()

# Let's go to postbox
$ChromeDriver.Navigate().GoToUrl("https://kunde.comdirect.de/itx/posteingangsuche")

# Wait for user to put in photoTAN
while( $true ) {
    try {
    #This ID only exists on the postbox, so if you can see it, you made it through
        if ($ChromeDriver.FindElementById("f1-zeitraumInput_pbInput")) {
            break
        }
    } catch {
        continue
    }
    sleep 1
}

$select = New-Object OpenQA.Selenium.Support.UI.SelectElement($ChromeDriver.FindElementById("f1-zeitraumInput_pbInput"))
[System.Collections.ArrayList]$time_options = @($select.Options)


$number = 0;
for ($i=0; $i -lt $time_options.Count; $i++) {
    if ($time_options[$i].GetAttribute('value') -eq 'DATUM') {
        $time_options.RemoveAt($i)
    }
}

if ($settings.range -ge 1 -and $settings.range -le $time_options.Count ) {
    $number = $settings.range;
} else {
    Write-Host "Bitte einen Zeitraum auswählen:"
    For ($i=0; $i -lt $time_options.Count; $i++)  {
    Write-Host "$($i+1): $($time_options[$i].getAttribute('text') + "-" + $time_options[$i].getAttribute('value'))"
    }

    [int]$number = Read-Host "Press the number to select a user: "

    Write-Host "You've selected $($time_options[$number-1].GetAttribute('value'))"
}


$select.SelectByValue($time_options[$number-1].GetAttribute('value'))
$ChromeDriver.FindElementById("f1-sucheStarten").Click()


$pdfURLs = $ChromeDriver.FindElementsByCssSelector("a[id*='urlAbfrage'][href*='dokumentenabruf']").getAttribute("href")

# Wait for user to put in photoTAN
while( $true ) {
    try {
        $rightbutton = $ChromeDriver.FindElementByCssSelector("a[id='f1-j_idt123_right']")
        $ChromeDriver.ExecuteScript("arguments[0].scrollIntoView();", $rightbutton)
        $ChromeDriver.ExecuteScript("arguments[0].click();", $rightbutton)
        $pdfURLs = $pdfURLs + $ChromeDriver.FindElementsByCssSelector("a[id*='urlAbfrage'][href*='dokumentenabruf']").getAttribute("href")
    } catch {
        Write-Output "No right button found"
        break
    }
}


# Grab the cookies we generate so we can use them to download the PDFs
# We need to convert them to a PS WebRequestSession
$cookies = $ChromeDriver.manage().Cookies.AllCookies
$session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
foreach ($cookieS in $cookies) {
    $cookie = New-Object System.Net.Cookie 
    $cookie.Name = $cookieS.Name
    $cookie.Value = $cookieS.Value
    $cookie.Domain= $cookieS.Domain
    $cookie.Path = $cookieS.Path
    $cookie.HttpOnly = $cookies.isHttpOnly
    $session.Cookies.Add($cookie)
}

Write-Output $($pdfURLs.Count.ToString() + " files found on the server")

# Now we actually download the PDFs using the websession from before
$counter = 0
foreach ($pdf in $pdfURLs) {
    $pdf = $pdf.split("?")[0]
    $text = $pdf.split("/")[-1]
    if (($pdf.split(".")[-1] -eq "pdf") -and !(Test-Path $postBoxDir\$text -PathType Leaf )) {
        wget $pdf -WebSession $session -OutFile $postBoxDir\$text
        $counter++
        Write-Output $("$counter : Downloaded " + $text)
    }
}
Write-Output $($counter.ToString() + " new files downloaded")

# Cleaning up after ourselves!
# Pause # Adding a stop, after pressing enter within the console the Selenium session will end everything will be closed
Function Stop-ChromeDriver {Get-Process -Name chromedriver -ErrorAction SilentlyContinue | Stop-Process -ErrorAction SilentlyContinue}
$ChromeDriver.Close() # Close selenium browser session method
$ChromeDriver.Quit() # End ChromeDriver process method
Stop-ChromeDriver # Function to make sure Chromedriver process is ended (double-tap!)
