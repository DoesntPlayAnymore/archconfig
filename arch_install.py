import os
import sys
import json
from itertools import chain


partition='/dev/nvme0n1p3'
distro='arch'
mount_point='/mnt'
root_json_file='btrfs_template.json'
user_json_file='btrfs_user.json'
users=['pro'],
boot_partition='/dev/nvme0n1p1'

HOSTNAME='archpad'
LOCALE='en_DK-UTF8 UTF-8'
LANG='en-US.UTF-8'
REGION='Europe'
CITY='Copenhagen'
KERNEL='linux-lts'
KERNEL_HEADERS='linux-lts-headers'



pacstrap_packages = ' '.join([
        'base',
        KERNEL,
        KERNEL_HEADERS,
        'linux-firmware',
        'git',
        'base-devel',
        'btrfs-progs',
        'bash-autocomplete'
])



chroot_packages = ' '.join([
        KERNEL_HEADERS,
        'git',
        'refind',
        'base-devel',
        'btrfs-progs',
        'iw',
        'gptfdisk',
        'zsh',
        'vim',
        'nvim',
        'terminus-font'
])



MKINITCPIO_CONFIG = [
        'MODULES=(btrfs)',
        'BINARIES=()',
        'FILES=()',
        'HOOKS=(base udev autodetect modconf block encrypt filesystems keyboard fsck)'
]



REFIND_CONFIG = '\n'.join([
        'timeout 20',
        'also_scan_dirs +,@/'
]



def main(
        partition,
        distro,
        mount_point,
        root_json_file,
        user_json_file,
        users=[],
        boot_partition=None
):
    rootvol = f'@{distro}'
    print(f'Creating {distro} btrfs system on {partition}.')
    
    # Read and parse subvolume json template files.
    with open(root_json_file) as f:
        raw_root_subvolumes = json.load(f)
    
    with open(user_json_file) as f:
        raw_user_subvolumes = json.load(f)

    root_subvolumes = eval_raw_subvolumes(raw_root_subvolumes, DISTRO=distro)
    users_subvolumes = []
    for user in users:
        user_subvolumes = eval_raw_subvolumes(raw_user_subvolumes, DISTRO=distro, USER=user)
        users_subvolumes.extend(user_subvolumes)
    
    subvolumes = list(chain(root_subvolumes, users_subvolumes))

    # Create subvolumes.
    #print(subvolumes)
    os.system(f'mkfs.btrfs -f {partition}')
    os.system(f'mount {partition} {mount_point}') 
    
    for sub in subvolumes:
        n = sub['subvolume_name']
        os.system(f'btrfs subvolume create {mount_point}/{n}')
    
    # Mount subvolumes.
    os.system(f'umount {mount_point}')
    for sub in subvolumes:
        opt_subvol = sub['subvolume_name']
        opt_additional = sub['mount_options']
        opt_mount_point = f'{mount_point}/{sub["mount_point"]}'
        o = f'mount -t btrfs -o x-mount.mkdir,{opt_additional},subvol={opt_subvol} {partition} {opt_mount_point}'
        print(o)
        os.system(o)
    
    # Mount boot partition.
    os.system(f'mount -o x-mount.mkdir {boot_partition} {mount_point}/boot')

    # Pacstrap
    os.system(f'pacstrap {mount_point} {pacstrap_packages}')    
    
    # Generate filesystem table.
    os.system(f'genfstab -U -p {mount_point} >> {mount_point}/etc/fstab'

    # Chroot into system.
    os.system(f'arch-chroot {mount_point}')
    exit(0)
    # Set localization
    os.system(f'echo {LOCALE} >> /etc/locale.gen')
    os.system(f'locale-gen')
    os.system(f'echo "LANG={LANG}" >> /etc/locale.conf')
    os.system(f'ln -sf /usr/share/zoneinfo/{REGION}/{CITY} /etc/localtime')
   
    # Host config
    os.system(f'echo "{HOSTNAME}" > /etc/hostname')
    os.system(f'echo "127.0.1.1 {HOSTNAME}.localdomain {HOSTNAME} >> /etc/hosts')
    
    # Install packages.
    os.system(f'pacman -Syyy')
    os.system(f'pacman -Syu {chroot_packages}')
    

    # Make initial cpio.
    os.system(f'cp /etc/mkinitcpio.conf /etc/mkinitcpio.conf.bak')
    
    for line in MKINITCPIO_CONFIG:
        os.system(f'echo {line} >> /etc/mkinitcpio.conf')
    
    os.system('mkinitcpio -p {KERNEL}')

    # Install boot loader.
    os.system('refind-install {boot_partition} --alldrivers')
    os.system('cp /boot/EFI/refind/refind.conf /boot/EFI/refind/refind.conf.bak')

    # ...
    print("Almost done...")


    return 0



def eval_raw_subvolumes(raw_subvolumes, **context):
    subvolumes = []
    for rawsub in raw_subvolumes:
        sub = {}
        for k,v in rawsub.items():
            sub[k] = eval(f'f"{v}"', context)
        subvolumes.append(sub)

    return subvolumes

"""
@rch					        :/
@rch/home				        :/home
@rch/home/pro				    :/home/pro
@rch/home/pro/Documents		:/home/pro/Documents
@rch/home/pro/Downloads		:/home/pro/Downloads
@rch/home/pro/data			:/home/pro/data
@rch/home/pro/cache			:/home/pro/.cache
@rch/var_log				:/var/log
@rch/var_cache				:/var/cache
@rch/snapshots				:/.snapshots
@rch/home/pro/snapshots		:/home/pro/.snapshots
@rch/home/pro/Documents/snapshots	:/home/pro/Documents/.snapshots
"""

if __name__=='__main__':
    import argparse

    ap = argparse.ArgumentParser(
            description="Create Linux btrfs file system layout."
    )

    ap.add_argument('partition', type=str)
    ap.add_argument('-d', '--distro', type=str)
    ap.add_argument('-m', '--mount-point', dest='mount_point', type=str, required=1)
    ap.add_argument('-r', '--root-subvols', dest='root_template', type=str)
    ap.add_argument('-u', '--user-subvols', dest='user_template', type=str)
    ap.add_argument('-U', '--users', type=str, nargs='*')
    ap.add_argument('-b', '--boot-partition', dest='boot_partition', type=str)
    parsed = ap.parse_args()

    exit(main(
            partition=parsed.partition,
    ))
