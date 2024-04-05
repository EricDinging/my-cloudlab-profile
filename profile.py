"""This is a trivial example of a gitrepo-based profile; The profile source code and other software, documentation, etc. are stored in in a publicly accessible GIT repository (say, github.com). When you instantiate this profile, the repository is cloned to all of the nodes in your experiment, to `/local/repository`. 

This particular profile is a simple example of using a single raw PC. It can be instantiated on any cluster; the node will boot the default operating system, which is typically a recent version of Ubuntu.

Instructions:
Wait for the profile instance to start, then click on the node in the topology and choose the `shell` menu item. 
"""

# Import the Portal object.
import geni.portal as portal
# Import the ProtoGENI library.
import geni.rspec.pg as rspec

image = ('urn:publicid:IDN+emulab.net+image+emulab-ops:UBUNTU20-64-STD', 'UBUNTU 20.04')

# Create a portal context.
pc = portal.Context()

pc.defineParameter("num_nodes", "Number of nodes",
                   portal.ParameterType.INTEGER, 1)
pc.defineParameter("user_names", "Usernames (split with space)",
                   portal.ParameterType.STRING, "ericdinging")
pc.defineParameter("project_group_name", "Project group name",
                   portal.ParameterType.STRING, "GAIA")
pc.defineParameter("os_image", "OS image",
                   portal.ParameterType.IMAGE, image)
pc.defineParameter("node_hw", "node type",
                   portal.ParameterType.NODETYPE, "r7525")
pc.defineParameter("data_size", "node local storage size",
                   portal.ParameterType.STRING, "256GB")
pc.defineParameter("has_nfs", "Whether to include a NFS node",
                   portal.ParameterType.BOOLEAN, False)
pc.defineParameter("nfs_hw", "NFS node type",
                   portal.ParameterType.NODETYPE, "c8220")
pc.defineParameter("nfs_size", "NFS size (create ephemeral storage)",
                   portal.ParameterType.STRING, "200GB")
pc.defineParameter("nfs_dataset", "NFS URN (back with remote dataset)",
                   portal.ParameterType.STRING, "")
params = pc.bindParameters()

# Create a Request object to start building the RSpec.
request = pc.makeRequestRSpec()

# Add lan
lan = request.LAN("nfsLan")
lan.best_effort = True
lan.vlan_tagging = True
lan.link_multiplexing = True

# add bluefield in case of r7525 hw type
# if params.node_hw == "r7525":
#     global linkbf
#     linkbf = request.Link('bluefield')
#     linkbf.type = "generic_100g"

if params.has_nfs:
    # nfs server with special block storage server
    nfsServer = request.RawPC("nfs")
    nfsServer.disk_image = params.os_image
    nfsServer.hardware_type = params.nfs_hw
    nfsServerInterface = nfsServer.addInterface()
    nfsServerInterface.addAddress(
        rspec.IPv4Address("192.168.1.250", "255.255.255.0"))
    lan.addInterface(nfsServerInterface)
    nfsServer.addService(rspec.Execute(
        shell="bash", command="/local/repository/setup-firewall.sh"))
    nfsServer.addService(rspec.Execute(
        shell="bash", command="/local/repository/nfs-server.sh"))
    
    # Special node that represents the ISCSI device where the dataset resides
    nfsDirectory = "/nfs"
    if params.nfs_dataset:
        dsnode = request.RemoteBlockstore("dsnode", nfsDirectory)
        dsnode.dataset = params.nfs_dataset
        dslink = request.Link("dslink")
        dslink.addInterface(dsnode.interface)
        dslink.addInterface(nfsServer.addInterface())
        # Special attributes for this link that we must use.
        dslink.best_effort = True
        dslink.vlan_tagging = True
        dslink.link_multiplexing = True
    else:
        bs = nfsServer.Blockstore("nfs-bs", nfsDirectory)
        bs.size = params.nfs_size

# Nodes
for i in range(params.num_nodes):
    node = request.RawPC(f"node-{i+1}")
    node.disk_image = params.os_image
    node.hardware_type = params.node_hw
    bs = node.Blockstore(f"bs-{i+1}", "/data")
    bs.size = params.data_size
    intf = node.addInterface("if1")
    # if node.hardware_type == "r7525":
    #     # r7525 requires special config to use its normal 25Gbps experimental network
    #     intf.bandwidth = 25600
    #     # Initialize BlueField DPU.
    #     bfif = node.addInterface("bf")
    #     bfif.addAddress(rspec.IPv4Address(
    #         f"192.168.10.{i+1}", "255.255.255.0"))
    #     bfif.bandwidth = 100000000
    #     linkbf.addInterface(bfif)
    
    intf.addAddress(rspec.IPv4Address(
        f"192.168.1.{i+1}", "255.255.255.0"))
    lan.addInterface(intf)

    # node.addService(rspec.Execute(
    #     shell="bash", command="/local/repository/setup-firewall.sh"))
    node.addService(rspec.Execute(
        shell="bash", command="/local/repository/nfs-client.sh"))
    node.addService(
        rspec.Execute(
            shell="bash",
            command="/local/repository/setup-node.sh {} {}".format(
                params.project_group_name, params.user_names)
        )
    )


# Install and execute a script that is contained in the repository.
# node.addService(pg.Execute(shell="sh", command="/local/repository/silly.sh"))

# Print the RSpec to the enclosing page.
pc.printRequestRSpec(request)
 # type: ignore