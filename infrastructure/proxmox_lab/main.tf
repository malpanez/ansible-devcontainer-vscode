terraform {
  required_version = "~> 1.7.0"

  required_providers {}
}

provider "proxmox" {}

locals {
  lab_vms = {
    for vm in var.virtual_machines : vm.name => vm
  }
}

resource "proxmox_vm_qemu" "lab" {
  for_each = local.lab_vms

  name        = each.value.name
  desc        = each.value.description
  target_node = each.value.node
  vmid        = each.value.vmid

  clone      = each.value.clone
  full_clone = true

  cores   = each.value.cores
  sockets = each.value.sockets
  memory  = each.value.memory_mebibytes
  balloon = coalesce(each.value.balloon_memory, each.value.memory_mebibytes)
  cpu     = each.value.cpu_type
  onboot  = true

  scsihw = each.value.scsi_controller

  disks {
    slot     = 0
    size     = each.value.disk_gib
    storage  = each.value.storage_pool
    type     = "scsi"
    format   = "qcow2"
    discard  = true
    ssd      = each.value.disk_is_ssd
    cache    = each.value.disk_cache_mode
    iothread = true
  }

  network {
    id     = 0
    model  = each.value.nic_model
    bridge = each.value.bridge
    tag    = each.value.vlan_tag
    rate   = each.value.network_rate_limit_mbps
  }

  ssh_user     = each.value.provision_user
  sshkeys      = var.authorized_ssh_keys
  nameserver   = var.nameservers
  searchdomain = var.search_domains

  agent     = each.value.enable_qemu_agent
  cloudinit = true

  lifecycle {
    ignore_changes = [
      network,
      sshkeys,
    ]
  }
}

output "vm_summary" {
  description = "Flattened metadata for each VM created by this module."
  value = {
    for name, vm in proxmox_vm_qemu.lab : name => {
      vmid         = vm.vmid
      node         = vm.target_node
      ip_config    = vm.ipconfig0
      mac_address  = vm.network[0].macaddr
      bridge       = vm.network[0].bridge
      disks        = [for disk in vm.disks : disk.storage]
      clone_source = vm.clone
    }
  }
}
