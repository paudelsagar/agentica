# MCP Toolbox for Databases

The **MCP Toolbox for Databases** allows AI agents in Agentica to interact with your MySQL (or other SQL) databases via MCP servers over **SSE**. It provides prebuilt queries as tools for common operations like listing users, accounts, transactions, and summaries.



---



## Setting up the MySQL Database

```mysql
-- Create database
CREATE DATABASE IF NOT EXISTS payment_system;

USE payment_system;

-- Users table
CREATE TABLE users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Accounts table
CREATE TABLE accounts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    account_id VARCHAR(50) UNIQUE NOT NULL,
    user_id BIGINT NOT NULL,
    account_type ENUM('WALLET', 'BANK', 'CARD') NOT NULL,
    currency CHAR(3) NOT NULL,
    status ENUM('ACTIVE','SUSPENDED','CLOSED') DEFAULT 'ACTIVE',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_accounts_user FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Merchants table
CREATE TABLE merchants (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    merchant_id VARCHAR(50) UNIQUE NOT NULL,
    merchant_name VARCHAR(100) NOT NULL,
    merchant_category VARCHAR(50),
    mcc_code VARCHAR(10),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Transaction types table
CREATE TABLE transaction_types (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    transaction_type_id VARCHAR(10) UNIQUE NOT NULL,
    description VARCHAR(50) NOT NULL
);

-- Payment methods table
CREATE TABLE payment_methods (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    payment_method_id VARCHAR(20) UNIQUE NOT NULL,
    description VARCHAR(50) NOT NULL
);

-- Channels table
CREATE TABLE channels (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    channel_id VARCHAR(20) UNIQUE NOT NULL,
    description VARCHAR(20) NOT NULL
);

-- Currencies table
CREATE TABLE currencies (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    currency CHAR(3) UNIQUE NOT NULL,
    name VARCHAR(50),
    symbol VARCHAR(5)
);

-- Transaction status table
CREATE TABLE transaction_status (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    status_id VARCHAR(20) UNIQUE NOT NULL,
    description VARCHAR(20) NOT NULL
);

-- User KYC table
CREATE TABLE user_kyc (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT NOT NULL,
    kyc_status ENUM('PENDING', 'VERIFIED', 'REJECTED') DEFAULT 'PENDING',
    document_type VARCHAR(50),
    document_number VARCHAR(50),
    document_file VARCHAR(255),
    verified_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_kyc_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Transactions table
CREATE TABLE transactions (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tran_id VARCHAR(50) UNIQUE NOT NULL,
    tran_date DATETIME NOT NULL,
    user_id BIGINT NOT NULL,
    account_id BIGINT NOT NULL,
    counterparty_user_id BIGINT,
    counterparty_account_id BIGINT,
    transaction_type_id BIGINT NOT NULL,
    payment_method_id BIGINT NOT NULL,
    merchant_id BIGINT,
    amount DECIMAL(18,2) NOT NULL,
    currency_id BIGINT NOT NULL,
    remark VARCHAR(255),
    channel_id BIGINT NOT NULL,
    transaction_status_id BIGINT NOT NULL,
    reference_tran_id BIGINT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_transactions_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_transactions_account FOREIGN KEY (account_id) REFERENCES accounts(id),
    CONSTRAINT fk_transactions_counterparty_user FOREIGN KEY (counterparty_user_id) REFERENCES users(id),
    CONSTRAINT fk_transactions_counterparty_account FOREIGN KEY (counterparty_account_id) REFERENCES accounts(id),
    CONSTRAINT fk_transactions_transaction_type FOREIGN KEY (transaction_type_id) REFERENCES transaction_types(id),
    CONSTRAINT fk_transactions_payment_method FOREIGN KEY (payment_method_id) REFERENCES payment_methods(id),
    CONSTRAINT fk_transactions_merchant FOREIGN KEY (merchant_id) REFERENCES merchants(id),
    CONSTRAINT fk_transactions_currency FOREIGN KEY (currency_id) REFERENCES currencies(id),
    CONSTRAINT fk_transactions_channel FOREIGN KEY (channel_id) REFERENCES channels(id),
    CONSTRAINT fk_transactions_status FOREIGN KEY (transaction_status_id) REFERENCES transaction_status(id),
    CONSTRAINT fk_transactions_reference FOREIGN KEY (reference_tran_id) REFERENCES transactions(id)
);
```

> ⚠️ **Tip:** Insert sample master data (transaction types, payment methods, channels, currencies, users, merchants, transactions) as needed for testing. This is identical to the previous guide’s SQL inserts.



---



## Setting up the MCP Toolbox Server

Run the MCP Toolbox as an SSE server so Agentica agents can connect remotely.

### Using Node/Npx

```bash
npx -y @toolbox-sdk/server --prebuilt sqlite --port 5005
```

### Using Docker (Optional)

```bash
docker run -p 5005:5005 -v /path/to/db:/data mcp/toolbox-server
```

> The server exposes all tools defined in `tools.yaml` over HTTP/SSE.



---



## Configuring `tools.yaml`

The `tools.yaml` maps database queries to MCP tools for agents:

```yaml
sources:
  local-mysql:
    kind: mysql
    host: 127.0.0.1
    port: 3306
    database: payment_system
    user: root
    password: Mysql@12345

tools:
  # Users
  all_users:
    kind: mysql-sql
    source: local-mysql
    description: List all registered users
    statement: |
      SELECT id, user_id, name, email, phone, created_at
      FROM users
      ORDER BY id;

  verified_users:
    kind: mysql-sql
    source: local-mysql
    description: List users with verified KYC
    statement: |
      SELECT u.id, u.user_id, u.name, u.email, u.phone, k.kyc_status, k.document_type
      FROM users u
      JOIN user_kyc k ON u.id = k.user_id
      WHERE k.kyc_status = 'VERIFIED';

  active_accounts:
    kind: mysql-sql
    source: local-mysql
    description: List all active accounts
    statement: |
      SELECT a.id, a.account_id, u.user_id AS owner_user_id, a.account_type, a.currency, a.status
      FROM accounts a
      JOIN users u ON a.user_id = u.id
      WHERE a.status = 'ACTIVE';

  all_transactions:
    kind: mysql-sql
    source: local-mysql
    description: List all transactions with user and merchant details
    statement: |
      SELECT t.tran_id, t.tran_date, u.user_id AS from_user, a.account_id AS from_account,
             cp_u.user_id AS to_user, cp_a.account_id AS to_account,
             tt.description AS transaction_type, pm.description AS payment_method,
             m.merchant_name, t.amount, c.currency, t.remark, ch.description AS channel,
             ts.description AS status
      FROM transactions t
      JOIN users u ON t.user_id = u.id
      JOIN accounts a ON t.account_id = a.id
      LEFT JOIN users cp_u ON t.counterparty_user_id = cp_u.id
      LEFT JOIN accounts cp_a ON t.counterparty_account_id = cp_a.id
      LEFT JOIN transaction_types tt ON t.transaction_type_id = tt.id
      LEFT JOIN payment_methods pm ON t.payment_method_id = pm.id
      LEFT JOIN merchants m ON t.merchant_id = m.id
      JOIN currencies c ON t.currency_id = c.id
      JOIN channels ch ON t.channel_id = ch.id
      JOIN transaction_status ts ON t.transaction_status_id = ts.id
      ORDER BY t.tran_date DESC;

  # Add other tools similarly (recent_transactions, transactions_by_user, p2p_transactions, etc.)
```