use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use std::net::{IpAddr, Ipv4Addr};

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Lan {
    pub network: Ipv4Addr,
    pub prefix: u8,
}
impl Lan {
    pub fn parse(value: &str) -> Result<Self> {
        let (address, prefix) = value
            .split_once('/')
            .ok_or_else(|| anyhow::anyhow!("Use an IPv4 subnet such as 10.0.0.0/24"))?;
        let network: Ipv4Addr = address.parse()?;
        let prefix: u8 = prefix.parse()?;
        ensure!(
            network.is_private() && (8..=30).contains(&prefix),
            "Only a private local IPv4 subnet is allowed"
        );
        let mask = u32::MAX << (32 - prefix);
        ensure!(
            u32::from(network) & mask == u32::from(network),
            "Subnet address contains host bits"
        );
        Ok(Self { network, prefix })
    }
    pub fn permits(&self, ip: IpAddr) -> bool {
        if ip.is_loopback() {
            return true;
        }
        let IpAddr::V4(ip) = ip else {
            return false;
        };
        if !ip.is_private() {
            return false;
        }
        let mask = u32::MAX << (32 - self.prefix);
        u32::from(ip) & mask == u32::from(self.network)
    }
}
pub fn equal_key(a: &str, b: &str) -> bool {
    a.len() == b.len() && a.bytes().zip(b.bytes()).fold(0u8, |v, (a, b)| v | (a ^ b)) == 0
}
pub fn new_key() -> Result<String> {
    let mut data = [0u8; 24];
    getrandom::fill(&mut data).map_err(|e| anyhow::anyhow!("Random key: {e}"))?;
    Ok(data.iter().map(|b| format!("{b:02x}")).collect())
}
#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn restrict_to_one_lan_not_vpn_or_public() {
        let lan = Lan::parse("10.0.0.0/24").unwrap();
        for ip in ["10.0.0.13", "127.0.0.1"] {
            assert!(lan.permits(ip.parse().unwrap()));
        }
        for ip in [
            "10.0.1.13",
            "100.64.0.1",
            "8.8.8.8",
            "192.168.1.2",
            "::ffff:10.0.0.13",
        ] {
            assert!(!lan.permits(ip.parse().unwrap()));
        }
        assert!(Lan::parse("0.0.0.0/0").is_err());
    }
}
