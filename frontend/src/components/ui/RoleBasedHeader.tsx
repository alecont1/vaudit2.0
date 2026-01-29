import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import Icon from '../AppIcon';

interface RoleBasedHeaderProps {
  userRole?: 'engineer' | 'admin' | 'both';
}

const RoleBasedHeader = ({ userRole = 'both' }: RoleBasedHeaderProps) => {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const location = useLocation();

  const navigationItems = [
    {
      label: 'Evidence Analysis',
      path: '/compliance-engineer-evidence-analysis-workspace',
      role: 'engineer',
      icon: 'FileSearch',
    },
    {
      label: 'Knowledge Base',
      path: '/administrator-knowledge-base-management-dashboard',
      role: 'admin',
      icon: 'Database',
    },
  ];

  const filteredNavItems = navigationItems.filter(
    (item) => userRole === 'both' || item.role === userRole
  );

  const isActivePath = (path: string) => location.pathname === path;

  const toggleMobileMenu = () => {
    setIsMobileMenuOpen(!isMobileMenuOpen);
  };

  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-[100] bg-card border-b border-border shadow-subtle">
        <div className="flex items-center justify-between h-16 px-4 lg:px-6">
          <Link
            to="/"
            className="flex items-center gap-3 hover:opacity-80 transition-opacity duration-150"
            aria-label="Auditec Dashboard Home"
          >
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary">
              <Icon name="Shield" size={24} color="white" strokeWidth={2.5} />
            </div>
            <span className="text-xl font-semibold text-foreground hidden sm:block">
              Auditec
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-2">
            {filteredNavItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-2 px-6 py-3 rounded-md font-medium transition-all duration-150 ease-smooth ${
                  isActivePath(item.path)
                    ? 'bg-primary text-primary-foreground shadow-interactive'
                    : 'text-text-secondary hover:bg-muted hover:text-foreground'
                }`}
              >
                <Icon name={item.icon} size={18} strokeWidth={2} />
                <span>{item.label}</span>
              </Link>
            ))}
          </nav>

          <button
            onClick={toggleMobileMenu}
            className="md:hidden p-2 rounded-md hover:bg-muted transition-colors duration-150"
            aria-label="Toggle mobile menu"
            aria-expanded={isMobileMenuOpen}
          >
            <Icon
              name={isMobileMenuOpen ? 'X' : 'Menu'}
              size={24}
              strokeWidth={2}
            />
          </button>
        </div>
      </header>

      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 z-[200] bg-black/50 animate-fade-in md:hidden"
          onClick={closeMobileMenu}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed top-0 right-0 bottom-0 z-[200] w-80 bg-card shadow-elevated transform transition-transform duration-300 ease-smooth md:hidden ${
          isMobileMenuOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          <div className="flex items-center justify-between p-4 border-b border-border">
            <span className="text-lg font-semibold text-foreground">
              Navigation
            </span>
            <button
              onClick={closeMobileMenu}
              className="p-2 rounded-md hover:bg-muted transition-colors duration-150"
              aria-label="Close mobile menu"
            >
              <Icon name="X" size={24} strokeWidth={2} />
            </button>
          </div>

          <nav className="flex-1 overflow-y-auto p-4">
            <div className="space-y-2">
              {filteredNavItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={closeMobileMenu}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-all duration-150 ease-smooth ${
                    isActivePath(item.path)
                      ? 'bg-primary text-primary-foreground shadow-interactive'
                      : 'text-text-secondary hover:bg-muted hover:text-foreground'
                  }`}
                >
                  <Icon name={item.icon} size={20} strokeWidth={2} />
                  <span>{item.label}</span>
                </Link>
              ))}
            </div>
          </nav>

          <div className="p-4 border-t border-border">
            <div className="flex items-center gap-3 px-4 py-3 bg-muted rounded-lg">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-primary text-primary-foreground font-semibold">
                {userRole === 'engineer' ? 'CE' : userRole === 'admin' ? 'SA' : 'U'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {userRole === 'engineer' ?'Compliance Engineer'
                    : userRole === 'admin' ?'System Administrator' :'User'}
                </p>
                <p className="text-xs text-text-secondary truncate">
                  {userRole === 'both' ? 'Full Access' : 'Role-based Access'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

export default RoleBasedHeader;