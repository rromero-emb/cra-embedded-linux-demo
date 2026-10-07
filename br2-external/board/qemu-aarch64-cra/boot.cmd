# Script de arranque de U-Boot (sesión 1: sin verificación de firma todavía)
echo "CRA demo: cargando kernel desde virtio 0:1"
setenv bootargs "root=/dev/vda1 rootwait ro console=ttyAMA0"
load virtio 0:1 ${kernel_addr_r} /boot/Image
booti ${kernel_addr_r} - ${fdtcontroladdr}
