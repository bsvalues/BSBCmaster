-- Supabase Schema for MCP Assessor Agent API
-- Based on the existing database structure

-- Enable Row Level Security
ALTER DATABASE postgres SET "app.jwt_secret" TO '${SUPABASE_JWT_SECRET}';

-- Users table for authentication
CREATE TABLE IF NOT EXISTS public.users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    hashed_password VARCHAR(256) NOT NULL,
    full_name VARCHAR(255),
    roles VARCHAR(255)[] DEFAULT ARRAY['user'],
    disabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Enable RLS on users table
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Users table policies
CREATE POLICY "Users can view their own data" ON public.users
    FOR SELECT USING (auth.uid()::text = id::text);
    
CREATE POLICY "Users can update their own data" ON public.users
    FOR UPDATE USING (auth.uid()::text = id::text);

-- Parcels table
CREATE TABLE IF NOT EXISTS public.parcels (
    id SERIAL PRIMARY KEY,
    parcel_id VARCHAR(50) UNIQUE NOT NULL,
    address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(50) NOT NULL,
    zip_code VARCHAR(20) NOT NULL,
    
    -- Assessment values
    land_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
    improvement_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
    total_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
    assessment_year INTEGER NOT NULL,
    
    -- Geographic coordinates
    latitude FLOAT,
    longitude FLOAT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create index for parcel_id
CREATE INDEX IF NOT EXISTS idx_parcels_parcel_id ON public.parcels(parcel_id);

-- Enable RLS on parcels table
ALTER TABLE public.parcels ENABLE ROW LEVEL SECURITY;

-- Parcels table policies
CREATE POLICY "Parcels are viewable by all authenticated users" ON public.parcels
    FOR SELECT USING (auth.role() IN ('user', 'admin', 'assessor'));
    
CREATE POLICY "Parcels are editable by admin and assessor" ON public.parcels
    FOR ALL USING (auth.role() IN ('admin', 'assessor'));

-- Properties table
CREATE TABLE IF NOT EXISTS public.properties (
    id SERIAL PRIMARY KEY,
    parcel_id INTEGER NOT NULL REFERENCES public.parcels(id) ON DELETE CASCADE,
    
    -- Property characteristics
    property_type VARCHAR(50) NOT NULL,
    year_built INTEGER,
    square_footage INTEGER,
    bedrooms INTEGER,
    bathrooms FLOAT,
    lot_size FLOAT,
    lot_size_unit VARCHAR(20),
    stories FLOAT,
    condition VARCHAR(50),
    quality VARCHAR(50),
    
    -- Zoning and taxation
    tax_district VARCHAR(50),
    zoning VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create index for parcel_id in properties
CREATE INDEX IF NOT EXISTS idx_properties_parcel_id ON public.properties(parcel_id);

-- Enable RLS on properties table
ALTER TABLE public.properties ENABLE ROW LEVEL SECURITY;

-- Properties table policies
CREATE POLICY "Properties are viewable by all authenticated users" ON public.properties
    FOR SELECT USING (auth.role() IN ('user', 'admin', 'assessor'));
    
CREATE POLICY "Properties are editable by admin and assessor" ON public.properties
    FOR ALL USING (auth.role() IN ('admin', 'assessor'));

-- Sales table
CREATE TABLE IF NOT EXISTS public.sales (
    id SERIAL PRIMARY KEY,
    parcel_id INTEGER NOT NULL REFERENCES public.parcels(id) ON DELETE CASCADE,
    
    -- Sale details
    sale_date DATE NOT NULL,
    sale_price NUMERIC(12, 2) NOT NULL,
    sale_type VARCHAR(50),
    transaction_id VARCHAR(50),
    
    -- Buyer and seller
    buyer_name VARCHAR(255),
    seller_name VARCHAR(255),
    
    -- Financing
    financing_type VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create index for parcel_id in sales
CREATE INDEX IF NOT EXISTS idx_sales_parcel_id ON public.sales(parcel_id);
CREATE INDEX IF NOT EXISTS idx_sales_sale_date ON public.sales(sale_date);

-- Enable RLS on sales table
ALTER TABLE public.sales ENABLE ROW LEVEL SECURITY;

-- Sales table policies
CREATE POLICY "Sales are viewable by all authenticated users" ON public.sales
    FOR SELECT USING (auth.role() IN ('user', 'admin', 'assessor'));
    
CREATE POLICY "Sales are editable by admin and assessor" ON public.sales
    FOR ALL USING (auth.role() IN ('admin', 'assessor'));

-- Accounts table
CREATE TABLE IF NOT EXISTS public.accounts (
    id SERIAL PRIMARY KEY,
    account_id VARCHAR(50) UNIQUE NOT NULL,
    owner_name VARCHAR(255),
    mailing_address VARCHAR(255),
    mailing_city VARCHAR(100),
    mailing_state VARCHAR(50),
    mailing_zip VARCHAR(20),
    
    -- Property details
    property_address VARCHAR(255),
    property_city VARCHAR(100),
    property_type VARCHAR(50),
    legal_description TEXT,
    
    -- Geographic coordinates
    latitude FLOAT,
    longitude FLOAT,
    
    -- Assessment details
    assessment_year INTEGER,
    assessed_value NUMERIC(12, 2),
    tax_amount NUMERIC(12, 2),
    tax_status VARCHAR(50),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create index for account_id
CREATE INDEX IF NOT EXISTS idx_accounts_account_id ON public.accounts(account_id);
CREATE INDEX IF NOT EXISTS idx_accounts_property_city ON public.accounts(property_city);
CREATE INDEX IF NOT EXISTS idx_accounts_property_type ON public.accounts(property_type);

-- Enable RLS on accounts table
ALTER TABLE public.accounts ENABLE ROW LEVEL SECURITY;

-- Accounts table policies
CREATE POLICY "Accounts are viewable by all authenticated users" ON public.accounts
    FOR SELECT USING (auth.role() IN ('user', 'admin', 'assessor'));
    
CREATE POLICY "Accounts are editable by admin and assessor" ON public.accounts
    FOR ALL USING (auth.role() IN ('admin', 'assessor'));

-- Property Images table
CREATE TABLE IF NOT EXISTS public.property_images (
    id SERIAL PRIMARY KEY,
    property_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50),
    
    -- Image details
    image_url VARCHAR(512),
    image_path VARCHAR(512),
    image_type VARCHAR(50),
    image_date DATE,
    
    -- Image metadata
    width INTEGER,
    height INTEGER,
    file_size INTEGER,  -- in bytes
    file_format VARCHAR(20),  -- e.g., "JPEG", "PNG"
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create indexes for property_images
CREATE INDEX IF NOT EXISTS idx_property_images_property_id ON public.property_images(property_id);
CREATE INDEX IF NOT EXISTS idx_property_images_account_id ON public.property_images(account_id);

-- Enable RLS on property_images table
ALTER TABLE public.property_images ENABLE ROW LEVEL SECURITY;

-- Property images table policies
CREATE POLICY "Property images are viewable by all authenticated users" ON public.property_images
    FOR SELECT USING (auth.role() IN ('user', 'admin', 'assessor'));
    
CREATE POLICY "Property images are editable by admin and assessor" ON public.property_images
    FOR ALL USING (auth.role() IN ('admin', 'assessor'));

-- Function to handle updating updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for all tables to update updated_at timestamp
CREATE TRIGGER update_parcels_updated_at
BEFORE UPDATE ON public.parcels
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_properties_updated_at
BEFORE UPDATE ON public.properties
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sales_updated_at
BEFORE UPDATE ON public.sales
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_accounts_updated_at
BEFORE UPDATE ON public.accounts
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_property_images_updated_at
BEFORE UPDATE ON public.property_images
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON public.users
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Assessments table (additional table that extends the existing structure)
CREATE TABLE IF NOT EXISTS public.assessments (
    id SERIAL PRIMARY KEY,
    property_id INTEGER NOT NULL REFERENCES public.properties(id) ON DELETE CASCADE,
    
    -- Assessment details
    assessment_year INTEGER NOT NULL,
    assessment_date DATE NOT NULL,
    assessed_land_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
    assessed_improvement_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
    assessed_total_value NUMERIC(12, 2) NOT NULL DEFAULT 0,
    
    -- Tax details
    tax_year INTEGER,
    tax_amount NUMERIC(12, 2),
    tax_status VARCHAR(50),
    
    -- Assessment metadata
    assessor_name VARCHAR(255),
    assessment_method VARCHAR(50),
    valuation_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create index for property_id in assessments
CREATE INDEX IF NOT EXISTS idx_assessments_property_id ON public.assessments(property_id);
CREATE INDEX IF NOT EXISTS idx_assessments_assessment_year ON public.assessments(assessment_year);

-- Enable RLS on assessments table
ALTER TABLE public.assessments ENABLE ROW LEVEL SECURITY;

-- Assessments table policies
CREATE POLICY "Assessments are viewable by all authenticated users" ON public.assessments
    FOR SELECT USING (auth.role() IN ('user', 'admin', 'assessor'));
    
CREATE POLICY "Assessments are editable by admin and assessor" ON public.assessments
    FOR ALL USING (auth.role() IN ('admin', 'assessor'));

CREATE TRIGGER update_assessments_updated_at
BEFORE UPDATE ON public.assessments
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();