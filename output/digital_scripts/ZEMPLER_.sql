INSERT INTO `digitalpdf$script` (`Id`,`Name`,`Commands`,`ModificationTimeUtc`,`IsDeleted`) VALUES (9999,'ZemplerBank','$source = "Zempler Bank"
$features = "REVERSE_ORDER"
$periodBufferDays = 5

// Delete footer text
delete all lines starting "Zempler Bank Ltd is registered"
delete all lines starting "Zempler Bank provides credit"
delete all lines containing "Prudential Regulation Authority"
delete all lines containing "Financial Conduct Authority"

// Get account name (the account holder name, not the company)
$accountName = get line starting "Account held under company name:" => get words after "name:" => get text

// Get account number
$accountNumber = get line starting "Account number:" => skip words 2 => get text

// Get period from/to
$periodFrom = get line starting "From" => get words after "From" => take words 1 => get date "dd/MM/yyyy"
$periodTo = get line starting "From" => get words after "to" => take words 1 => get date "dd/MM/yyyy"

// Get opening and closing balances
$openingBalance = get line starting "Opening Balance:" => skip words 2 => get decimal
$closingBalance = get line starting "Closing Balance:" => skip words 2 => get decimal

// Find the top of the transactions table (below the header row)
@transactionsTop = get line starting "Date Card ending in" => bottom => get line below

// Find the bottom of the transactions table (last line before footer)
go to last page
@transactionsBottom = get line above 0

// Discard page header (repeat header row on each page)
get last line starting "Date Card ending in" => bottom => ignore header above

// Discard page footer
get line above 0 => top => ignore footer below

// Read the transactions table
$transactions = get multi page table @transactionsTop @transactionsBottom 0 90 170 450 530 page.right => describe table false "*Date[dd/MM/yyyy]" - Details **#Amount #Balance
',UTC_TIMESTAMP(),0);

INSERT INTO `digitalpdf$documentidentification` (`Id`,`Name`,`TitlePattern`,`AuthorPattern`,`CreatorPattern`,`ProducerPattern`,`Version`,`PageCount`,`SignatureInfo`,`ContainsText`,`ExcludesText`,`ScriptId`,`VerificationRuleSetId`,`ModificationTimeUtc`,`IsDeleted`) VALUES (9999,'ZemplerBank',NULL,NULL,'.*','.*',NULL,NULL,NULL,'["Zempler Bank","Opening Balance:","Closing Balance:","Card ending in","Business Account"]',NULL,9999,4,UTC_TIMESTAMP(),0);
