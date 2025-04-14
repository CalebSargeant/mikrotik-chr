:delay 5
:foreach iface in=[/interface ethernet find where running=yes] do={
  /ip dhcp-client add interface=[/interface get $iface name] disabled=no
  /system script remove startup-dhcp
  :log info "DHCP setup done on [/interface get $iface name]"
  break
}