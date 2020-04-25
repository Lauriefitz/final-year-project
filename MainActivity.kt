package com.example.alexaadmin

import android.app.Activity
import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.text.TextUtils
import android.util.Log
import android.webkit.MimeTypeMap
import android.widget.ImageView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.amazonaws.AmazonServiceException
import com.amazonaws.mobile.client.AWSMobileClient
import com.amazonaws.mobile.client.Callback
import com.amazonaws.mobile.client.UserStateDetails
import com.amazonaws.mobile.config.AWSConfiguration
import com.amazonaws.mobileconnectors.appsync.AWSAppSyncClient
import com.amazonaws.mobileconnectors.s3.transferutility.TransferListener
import com.amazonaws.mobileconnectors.s3.transferutility.TransferService
import com.amazonaws.mobileconnectors.s3.transferutility.TransferState
import com.amazonaws.mobileconnectors.s3.transferutility.TransferUtility
import com.amazonaws.services.s3.AmazonS3
import com.amazonaws.services.s3.AmazonS3Client
import com.amazonaws.services.s3.model.DeleteObjectRequest
import com.amazonaws.util.IOUtils
import kotlinx.android.synthetic.main.activity_image.*
import org.jetbrains.anko.AnkoLogger
import org.jetbrains.anko.info
import java.io.File
import java.io.FileOutputStream
import java.io.IOException


class MainActivity : AppCompatActivity(), AnkoLogger {

    private lateinit var mAWSAppSyncClient: AWSAppSyncClient
    private var fileUri: Uri? = null
    private var bitmap: Bitmap? = null
    private val CHOOSING_IMAGE_REQUEST = 1234
    var tv_file_name = ""
    private var s3Client: AmazonS3Client? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_image)

        mAWSAppSyncClient = AWSAppSyncClient.builder()
            .context(applicationContext)
            .awsConfiguration(AWSConfiguration(applicationContext))
            .build()
        info("AWS")

        applicationContext.startService(
            Intent(
                applicationContext,
                TransferService::class.java
            )
        )

        //AWSMobileClient.getInstance().credentials

        // Initialize the AWSMobileClient if not initialized
        AWSMobileClient.getInstance().initialize(
            applicationContext,
            object : Callback<UserStateDetails> {
                override fun onResult(userStateDetails: UserStateDetails) {
                    Log.i(
                        loggerTag,
                        "AWSMobileClient initialized. User State is " + userStateDetails.userState
                    )
                    //uploadFile()
                }

                override fun onError(e: java.lang.Exception) {
                    Log.e(loggerTag, "Initialization error.", e)
                }
            })


        btn_choose_file.setOnClickListener {
            showChoosingFile()
        }

        upload.setOnClickListener {
            info("Upload button pressed")
            setResult(RESULT_OK)
            uploadFile()
//            finish()
        }

        delete.setOnClickListener {
            info("Delete button pressed")
            deleteFile()
        }
//
        btn_download.setOnClickListener {
            info("download button pressed")
            downloadFile()
//            finish()
        }
    }

    private fun uploadFile() {

        val fileName = edt_file_name.text.toString()

        val file = File(applicationContext.filesDir, fileName)

        createFile(applicationContext, fileUri!!, file)

        val transferUtility = TransferUtility.builder()
            .context(applicationContext)
            .awsConfiguration(AWSMobileClient.getInstance().configuration)
            .s3Client(AmazonS3Client(AWSMobileClient.getInstance()))
            .build()

        val uploadObserver =
            transferUtility.upload(fileName + "." + getFileExtension(fileUri), file)

        uploadObserver.setTransferListener(object : TransferListener {

            override fun onStateChanged(id: Int, state: TransferState) {
                if (TransferState.COMPLETED == state) {
                    Toast.makeText(applicationContext, "Upload Completed!", Toast.LENGTH_SHORT)
                        .show()

                    //file.delete()
                } else if (TransferState.FAILED == state) {
                    file.delete()
                }
            }

            override fun onProgressChanged(id: Int, bytesCurrent: Long, bytesTotal: Long) {
                val percentDonef = bytesCurrent.toFloat() / bytesTotal.toFloat() * 100
                val percentDone = percentDonef.toInt()

                tv_file_name =
                    "ID:$id|bytesCurrent: $bytesCurrent|bytesTotal: $bytesTotal|$percentDone%"
            }

            override fun onError(id: Int, ex: Exception) {
                ex.printStackTrace()
            }

        })
    }

    private fun downloadFile() {

        val fileName = edt_file_name.text.toString()

        val path = getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS)

        val file = File(path, "$fileName.jpg")

        val transferUtility = TransferUtility.builder()
            .context(applicationContext)
            .awsConfiguration(AWSMobileClient.getInstance().configuration)
            .s3Client(AmazonS3Client(AWSMobileClient.getInstance()))
            .build()

        val dObserver = transferUtility.download("$fileName.jpg", file)


        dObserver.setTransferListener(object : TransferListener {

            override fun onStateChanged(id: Int, state: TransferState) {
                if (TransferState.COMPLETED == state) {
                    if (file.exists()) {
                        val myBitmap = BitmapFactory.decodeFile(file.absolutePath)
                        val myImage: ImageView = findViewById<ImageView>(R.id.img_file)
                        myImage.setImageBitmap(myBitmap)
                    }
                    Toast.makeText(applicationContext, "Download Completed!", Toast.LENGTH_SHORT)
                        .show()

                } else if (TransferState.FAILED == state) {
                }
            }

            override fun onProgressChanged(id: Int, bytesCurrent: Long, bytesTotal: Long) {
                val percentDonef = bytesCurrent.toFloat() / bytesTotal.toFloat() * 100
                val percentDone = percentDonef.toInt()

                tv_file_name =
                    "ID:$id|bytesCurrent: $bytesCurrent|bytesTotal: $bytesTotal|$percentDone%"
            }

            override fun onError(id: Int, ex: Exception) {
                ex.printStackTrace()
            }

        })
    }

    private fun deleteFile() {
        val fileName = edt_file_name.text.toString()
        val path = getExternalFilesDir(Environment.DIRECTORY_DOCUMENTS)
        val file = File(path, "$fileName.jpg")
        val s3: AmazonS3? = null
        val bucketName = "alexa-admin-2007563204634-env"
        val key = "persontest.jpg"
        try {
//            val deleteObjectRequest: DeleteObjectRequest? =
//                DeleteObjectRequest(bucketName, key).withKey(key)
//            s3?.deleteObject(deleteObjectRequest)
            s3Client?.deleteObject(bucketName, key)
            file.delete()
            img_file.setImageResource(0)
            info("Deleted")

        } catch (ase: AmazonServiceException) {
            info("Caught an AmazonServiceException from PUT requests, rejected reasons:")
        }

    }

    private fun showChoosingFile() {
        val intent = Intent()
        intent.type = "image/*"
        intent.action = Intent.ACTION_GET_CONTENT
        startActivityForResult(Intent.createChooser(intent, "Select Image"), CHOOSING_IMAGE_REQUEST)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)

        bitmap?.recycle()

        if (requestCode == CHOOSING_IMAGE_REQUEST && resultCode == Activity.RESULT_OK && data != null && data.data != null) {
            fileUri = data.data
            try {
                bitmap = MediaStore.Images.Media.getBitmap(contentResolver, fileUri)

            } catch (e: IOException) {
                e.printStackTrace()
            }

        }
    }

    private fun createFile(context: Context, srcUri: Uri?, dstFile: File) {
        try {
            val inputStream = context.contentResolver.openInputStream(srcUri!!) ?: return
            val outputStream = FileOutputStream(dstFile)
            IOUtils.copy(inputStream, outputStream)
            inputStream.close()
            outputStream.close()
            val bmp = BitmapFactory.decodeFile(dstFile.absolutePath)
            img_file.setImageBitmap(bmp)
        } catch (e: IOException) {
            e.printStackTrace()
        }
    }

    private fun getFileExtension(uri: Uri?): String {
        val contentResolver = contentResolver
        val mime = MimeTypeMap.getSingleton()

        return mime.getExtensionFromMimeType(contentResolver.getType(uri!!)).toString()
    }
}


