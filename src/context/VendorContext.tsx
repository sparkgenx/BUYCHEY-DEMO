import { createContext, useContext, useState, ReactNode } from 'react';

interface Vendor {
  id: number;
  name: string;
  username: string;
}

interface VendorContextType {
  vendor: Vendor | null;
  login: (vendor: Vendor) => void;
  logout: () => void;
}

const VendorContext = createContext<VendorContextType | undefined>(undefined);

export function VendorProvider({ children }: { children: ReactNode }) {
  const [vendor, setVendor] = useState<Vendor | null>(() => {
    const storedVendor = localStorage.getItem('vendor');

    if (!storedVendor) {
      return null;
    }

    try {
      return JSON.parse(storedVendor) as Vendor;
    } catch {
      localStorage.removeItem('vendor');
      return null;
    }
  });

  const login = (vendor: Vendor) => {
    setVendor(vendor);
    localStorage.setItem('vendor', JSON.stringify(vendor));
  };

  const logout = () => {
    setVendor(null);
    localStorage.removeItem('vendor');
  };

  return (
    <VendorContext.Provider value={{ vendor, login, logout }}>
      {children}
    </VendorContext.Provider>
  );
}

export function useVendor() {
  const context = useContext(VendorContext);
  if (!context) {
    throw new Error('useVendor must be used within VendorProvider');
  }
  return context;
}
