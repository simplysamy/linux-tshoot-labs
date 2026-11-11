# Disposable lab VM. The labs break this machine on purpose - never run them on a real server.
#   vagrant up          # build (first time ~5 min)
#   vagrant ssh         # log in, then: cd /lab && sudo ./labctl.sh list
#   vagrant destroy -f  # throw it away and start fresh
Vagrant.configure("2") do |config|
  config.vm.box      = "bento/ubuntu-24.04"
  config.vm.hostname = "tshoot-lab"

  config.vm.provider "virtualbox" do |vb|
    vb.name   = "tshoot-lab"
    vb.memory = 2048
    vb.cpus   = 2
  end
  config.vm.provider "hyperv" do |hv|
    hv.vmname = "tshoot-lab"
    hv.memory = 2048
    hv.cpus   = 2
  end

  config.vm.synced_folder ".", "/lab"
  config.vm.provision "shell", path: "setup/install-base.sh"
end
