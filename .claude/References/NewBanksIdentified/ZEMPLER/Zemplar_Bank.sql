INSERT INTO `digitalpdf$script` (`Id`,`Name`,`Commands`,`ModificationTimeUtc`,`IsDeleted`) 
VALUES 
(9999,
'ZemplerBank',
'$source = "Zempler Bank"
$features = "REVERSE_ORDER"

// Delete footer text
delete all lines starting "Zempler Bank Ltd is registered"
delete all lines starting "Zempler Bank provides credit"

// Get account name (the account holder name, not the company)
$accountName = get line starting "Account held under company name:" => get words after "name:" => get text

// Get account number
$accountNumber = get line starting "Account number:" => skip words 2 => get text

// Get period from/to
$periodFrom = get line containing "From" => get words after "From" => take words 1 => get date "dd/MM/yyyy"
$periodTo = get line containing "From" => get words after "to" => take words 1 => get date "dd/MM/yyyy"

// Get opening and closing balances
$openingBalance = get line starting "Opening Balance:" => take last words 1 => get decimal
$closingBalance = get line starting "Closing Balance:" => take last words 1 => get decimal

// Discard header block above transaction table
@transactionsTop = get line containing "Date Card ending in" => bottom => get line below

// Discard page header on subsequent pages
get last line containing "Date Card ending in" => bottom => ignore header above

// Discard footer
get line above 0 => top => ignore footer below

// Get end of table
go to last page
@transactionsBottom = get line above 0

// Remove header rows on every page
delete all lines starting "Date Card ending in"

// Read the transactions
$transactions = get multi page table @transactionsTop @transactionsBottom 0 90 155 430 500 page.right => describe table false "*Date[dd/MM/yyyy]" - Details **#Amount #Balance
'
,UTC_TIMESTAMP(),0);

INSERT INTO `digitalpdf$documentidentification` (`Id`,`Name`,`TitlePattern`,`AuthorPattern`,`CreatorPattern`,`ProducerPattern`,`Version`,`PageCount`,`SignatureInfo`,`ContainsText`,`ExcludesText`,`ScriptId`,`VerificationRuleSetId`,`ModificationTimeUtc`,`IsDeleted`) VALUES (9999,'ZemplerBank',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'[\"Zempler Bank\",\"Opening Balance:\",\"Closing Balance:\",\"Card ending in\",\"Business Account\"]',NULL,9999,4,UTC_TIMESTAMP(),0);