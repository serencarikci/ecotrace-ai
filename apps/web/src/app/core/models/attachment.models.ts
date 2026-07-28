export interface ActivityAttachment {
  id: string;
  organizationId: string;
  activityRecordId: string;
  originalFileName: string;
  storedFileName: string;
  contentType: string;
  fileSize: number;
  checksum: string;
  uploadedByUserId: string | null;
  isDeleted: boolean;
  createdAt: string;
}
