"use client";
import React, { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import {
  createUpload,
  triggerProcessing,
  uploadToPresignedUrl,
  isApiError,
} from "@/lib/api";
import type { DocumentRecord } from "@/lib/types";
import { useToast } from "@/components/ui/toast-provider";

interface UploadButtonProps {
  onUploadStart?: (tempId: string, filename: string) => void;
  onUploadReady?: (tempId: string, document: DocumentRecord) => void;
  onUploadComplete?: (tempId: string, document: DocumentRecord) => void;
  onUploadError?: (tempId: string, message: string) => void;
}

export default function UploadButton({
  onUploadStart,
  onUploadReady,
  onUploadComplete,
  onUploadError,
}: UploadButtonProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const { notify } = useToast();
  const queryClient = useQueryClient();
  const [isUploading, setIsUploading] = useState(false);

  const resetInput = () => {
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUploadError = (tempId: string, message: string) => {
    notify({
      title: "Upload failed",
      description: message,
      variant: "destructive",
    });
    onUploadError?.(tempId, message);
    setIsUploading(false);
    resetInput();
  };

  async function handleFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    const isTxtFile = file.name.toLowerCase().endsWith(".txt");
    if (!isTxtFile) {
      notify({
        title: "Invalid file type",
        description: "Only .txt files are supported for upload.",
        variant: "destructive",
      });
      resetInput();
      return;
    }

    const tempId = `temp-${crypto.randomUUID()}`;
    onUploadStart?.(tempId, file.name);
    setIsUploading(true);

    let uploadInitResponse: { job_id: string; pre_signed_url: string } | null = null;
    let initialDoc: DocumentRecord | null = null;
    try {
      const response = await createUpload(file.name);
      uploadInitResponse = {
        job_id: response.job_id,
        pre_signed_url: response.pre_signed_url,
      };
      initialDoc = {
        job_id: response.job_id,
        filename: file.name,
        status: "uploading",
      };
      onUploadReady?.(tempId, initialDoc);
    } catch (error) {
      const message = isApiError(error)
        ? `Error: Could not initiate upload. ${error.message}`
        : "Error: Could not initiate upload. Please try again.";
      handleUploadError(tempId, message);
      return;
    }

    if (!uploadInitResponse || !initialDoc) {
      handleUploadError(tempId, "Error: Could not initiate upload. Please try again.");
      return;
    }

    try {
      await uploadToPresignedUrl(uploadInitResponse.pre_signed_url, file);
    } catch (error) {
      handleUploadError(tempId, "Error: File upload failed. Please try again.");
      return;
    }

    let finalStatus = "processing";
    try {
      await triggerProcessing(uploadInitResponse.job_id);
      notify({
        title: "Processing started",
        description: `${file.name} is now being processed.`,
      });
    } catch (error) {
      const message = isApiError(error)
        ? error.message
        : "Could not start backend processing. You can retry from the processing view.";
      notify({
        title: "Processing not triggered",
        description: message,
        variant: "destructive",
      });
      finalStatus = "pending";
    }

    onUploadComplete?.(tempId, {
      ...initialDoc,
      status: finalStatus,
    });
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    setIsUploading(false);
    resetInput();
  }

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".txt"
        onChange={handleFileChange}
        className="hidden"
      />
      <Button
        type="button"
        size="sm"
        onClick={() => fileInputRef.current?.click()}
        disabled={isUploading}
      >
        {isUploading ? "Uploading…" : "+ New Upload"}
      </Button>
    </>
  );
}
