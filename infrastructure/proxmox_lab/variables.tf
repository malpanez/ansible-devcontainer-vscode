variable "pm_api_url" {
  description = "Base URL for the Proxmox API (e.g. https://proxmox.example:8006/api2/json)."
  type        = string
}

variable "pm_user" {
  description = "Username with API access (omit realm; handled via token ID)."
  type        = string
}

variable "pm_token_id" {
  description = "API token ID (formatted as user@realm!tokenid)."
  type        = string
  sensitive   = true
}

variable "pm_token_secret" {
  description = "API token secret."
  type        = string
  sensitive   = true
}

variable "pm_tls_insecure" {
  description = "Allow insecure TLS connections to the Proxmox API."
  type        = bool
  default     = false
}

variable "pm_timeout" {
  description = "Timeout (seconds) for API calls."
  type        = number
  default     = 60
}

variable "pm_log_enable" {
  description = "Enable provider logging."
  type        = bool
  default     = false
}

variable "pm_log_file" {
  description = "Optional log file path when logging is enabled."
  type        = string
  default     = ""
}

variable "pm_log_levels" {
  description = "Map of log categories to levels when logging is enabled."
  type        = map(string)
  default     = {}
}

variable "pm_parallel" {
  description = "Number of parallel API calls."
  type        = number
  default     = 4
}

variable "pm_task_timeout" {
  description = "Timeout (seconds) for Proxmox tasks."
  type        = number
  default     = 180
}

variable "pm_http_headers" {
  description = "Additional HTTP headers for API calls."
  type        = map(string)
  default     = {}
}

variable "pm_api_token_ttl" {
  description = "Optional TTL for auto-generated API tokens (seconds)."
  type        = number
  default     = null
}

variable "pm_api_token_renew" {
  description = "Automatically renew API tokens when TTL is set."
  type        = bool
  default     = false
}

variable "authorized_ssh_keys" {
  description = "Combined SSH public keys added during cloud-init provisioning."
  type        = string
  default     = ""
}

variable "nameservers" {
  description = "List of DNS servers passed to cloud-init."
  type        = list(string)
  default     = ["1.1.1.1", "1.0.0.1"]
}

variable "search_domains" {
  description = "Search domains appended to the network configuration."
  type        = list(string)
  default     = []
}

variable "virtual_machines" {
  description = "Virtual machine definitions to clone from existing templates."
  type = list(object({
    name                    = string
    description             = optional(string, "")
    node                    = string
    vmid                    = number
    clone                   = string
    cpu_type                = optional(string, "x86-64-v3")
    cores                   = number
    sockets                 = optional(number, 1)
    memory_mebibytes        = number
    balloon_memory          = optional(number)
    scsi_controller         = optional(string, "virtio-scsi-single")
    disk_gib                = number
    disk_is_ssd             = optional(bool, true)
    disk_cache_mode         = optional(string, "none")
    storage_pool            = string
    nic_model               = optional(string, "virtio")
    bridge                  = string
    vlan_tag                = optional(number)
    network_rate_limit_mbps = optional(number, 0)
    provision_user          = optional(string, "vscode")
    enable_qemu_agent       = optional(bool, true)
  }))
  default = []
}
