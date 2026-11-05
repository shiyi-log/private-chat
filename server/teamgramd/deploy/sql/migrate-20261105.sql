-- Add the invite-request state columns to databases created before the
-- corresponding columns were added to 1_teamgram.sql.
SET @chat_invite_schema = DATABASE();

SET @has_chat_invite_requested = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @chat_invite_schema
    AND table_name = 'chat_invite_participants'
    AND column_name = 'requested'
);
SET @chat_invite_requested_ddl = IF(
  @has_chat_invite_requested = 0,
  'ALTER TABLE `chat_invite_participants` ADD COLUMN `requested` tinyint(1) NOT NULL DEFAULT ''0'' AFTER `user_id`',
  'SELECT 1'
);
PREPARE chat_invite_requested_stmt FROM @chat_invite_requested_ddl;
EXECUTE chat_invite_requested_stmt;
DEALLOCATE PREPARE chat_invite_requested_stmt;

SET @has_chat_invite_approved_by = (
  SELECT COUNT(*)
  FROM information_schema.columns
  WHERE table_schema = @chat_invite_schema
    AND table_name = 'chat_invite_participants'
    AND column_name = 'approved_by'
);
SET @chat_invite_approved_by_ddl = IF(
  @has_chat_invite_approved_by = 0,
  'ALTER TABLE `chat_invite_participants` ADD COLUMN `approved_by` bigint(20) NOT NULL DEFAULT ''0'' AFTER `requested`',
  'SELECT 1'
);
PREPARE chat_invite_approved_by_stmt FROM @chat_invite_approved_by_ddl;
EXECUTE chat_invite_approved_by_stmt;
DEALLOCATE PREPARE chat_invite_approved_by_stmt;
